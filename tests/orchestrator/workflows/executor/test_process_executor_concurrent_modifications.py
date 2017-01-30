# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import json

import fasteners
import pytest

from aria.storage.exceptions import StorageError
from aria.orchestrator import events
from aria.orchestrator.workflows.exceptions import ExecutorException
from aria.orchestrator.workflows import api
from aria.orchestrator.workflows.executor import process
from aria.orchestrator import workflow, operation

import tests
from tests.orchestrator.context import execute as execute_workflow
from tests.orchestrator.workflows.helpers import events_collector
from tests import mock
from tests import storage


def test_concurrent_modification_on_task_succeeded(context, executor, shared_file):
    _test(context, executor, shared_file, _test_task_succeeded, expected_failure=True)


@operation
def _test_task_succeeded(ctx, shared_file, key, first_value, second_value):
    _concurrent_update(shared_file, ctx.node_instance, key, first_value, second_value)


def test_concurrent_modification_on_task_failed(context, executor, shared_file):
    _test(context, executor, shared_file, _test_task_failed, expected_failure=True)


@operation
def _test_task_failed(ctx, shared_file, key, first_value, second_value):
    first = _concurrent_update(shared_file, ctx.node_instance, key, first_value, second_value)
    if not first:
        raise RuntimeError('MESSAGE')


def test_concurrent_modification_on_update_and_refresh(context, executor, shared_file):
    _test(context, executor, shared_file, _test_update_and_refresh, expected_failure=False)


@operation
def _test_update_and_refresh(ctx, shared_file, key, first_value, second_value):
    node_instance = ctx.node_instance
    first = _concurrent_update(shared_file, node_instance, key, first_value, second_value)
    if not first:
        try:
            ctx.model.node_instance.update(node_instance)
        except StorageError as e:
            assert 'Version conflict' in str(e)
            ctx.model.node_instance.refresh(node_instance)
        else:
            raise RuntimeError('Unexpected')


def _test(context, executor, shared_file, func, expected_failure):
    def _node_instance(ctx):
        return ctx.model.node_instance.get_by_name(mock.models.DEPENDENCY_NODE_INSTANCE_NAME)

    shared_file.write(json.dumps({}))
    key = 'key'
    first_value = 'value1'
    second_value = 'value2'
    inputs = {
        'shared_file': str(shared_file),
        'key': key,
        'first_value': first_value,
        'second_value': second_value
    }

    @workflow
    def mock_workflow(ctx, graph):
        op = 'test.op'
        node_instance = _node_instance(ctx)
        node_instance.node.operations[op] = {'operation': '{0}.{1}'.format(__name__, func.__name__)}
        graph.add_tasks(
            api.task.OperationTask.node_instance(instance=node_instance, name=op, inputs=inputs),
            api.task.OperationTask.node_instance(instance=node_instance, name=op, inputs=inputs))

    signal = events.on_failure_task_signal
    with events_collector(signal) as collected:
        try:
            execute_workflow(mock_workflow, context, executor)
        except ExecutorException:
            pass

    props = _node_instance(context).runtime_properties
    assert props[key] == first_value

    exceptions = [event['kwargs']['exception'] for event in collected.get(signal, [])]
    if expected_failure:
        assert exceptions
        exception = exceptions[-1]
        assert isinstance(exception, StorageError)
        assert 'Version conflict' in str(exception)
    else:
        assert not exceptions


@pytest.fixture
def executor():
    result = process.ProcessExecutor(python_path=[tests.ROOT_DIR])
    yield result
    result.close()


@pytest.fixture
def context(tmpdir):
    result = mock.context.simple(storage.get_sqlite_api_kwargs(str(tmpdir)))
    yield result
    storage.release_sqlite_storage(result.model)


@pytest.fixture
def shared_file(tmpdir):
    return tmpdir.join('shared_file')


def _concurrent_update(shared_file, node_instance, key, first_value, second_value):
    def lock():
        return fasteners.InterProcessLock(shared_file)

    def get(key):
        with open(shared_file) as f:
            return json.load(f).get(key)

    def set(key):
        with open(shared_file) as f:
            content = json.load(f)
        content[key] = True
        with open(shared_file, 'wb') as f:
            json.dump(content, f)

    def wait_for(key):
        while True:
            time.sleep(0.01)
            with lock():
                if get(key):
                    break

    with lock():
        first = not get('first_in')
        set('first_in' if first else 'second_in')

    if first:
        wait_for('second_in')

    node_instance.runtime_properties[key] = first_value if first else second_value

    if first:
        with lock():
            set('first_out')
    else:
        wait_for('first_out')

    return first
