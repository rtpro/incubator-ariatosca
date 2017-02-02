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

from datetime import datetime

import pytest

from aria import application_model_storage
from aria.orchestrator import context
from aria.storage.sql_mapi import SQLAlchemyModelAPI
from tests import storage as test_storage
from tests.mock import models


class TestWorkflowContext(object):

    def test_execution_creation_on_workflow_context_creation(self, storage):
        ctx = self._create_ctx(storage)
        execution = storage.execution.get(ctx.execution.id)             # pylint: disable=no-member
        assert execution.deployment == storage.deployment.get_by_name(models.DEPLOYMENT_NAME)
        assert execution.workflow_name == models.WORKFLOW_NAME
        assert execution.blueprint == storage.blueprint.get_by_name(models.BLUEPRINT_NAME)
        assert execution.status == storage.execution.model_cls.PENDING
        assert execution.parameters == {}
        assert execution.created_at <= datetime.utcnow()

    def test_subsequent_workflow_context_creation_do_not_fail(self, storage):
        self._create_ctx(storage)
        self._create_ctx(storage)

    @staticmethod
    def _create_ctx(storage):
        """

        :param storage:
        :return WorkflowContext:
        """
        return context.workflow.WorkflowContext(
            name='simple_context',
            model_storage=storage,
            resource_storage=None,
            deployment_id=storage.deployment.get_by_name(models.DEPLOYMENT_NAME).id,
            workflow_name=models.WORKFLOW_NAME,
            task_max_attempts=models.TASK_MAX_ATTEMPTS,
            task_retry_interval=models.TASK_RETRY_INTERVAL
        )


@pytest.fixture(scope='function')
def storage():
    api_kwargs = test_storage.get_sqlite_api_kwargs()
    workflow_storage = application_model_storage(SQLAlchemyModelAPI, driver_kwargs=api_kwargs)
    workflow_storage.blueprint.put(models.get_blueprint())
    blueprint = workflow_storage.blueprint.get_by_name(models.BLUEPRINT_NAME)
    workflow_storage.deployment.put(models.get_deployment(blueprint))
    yield workflow_storage
    test_storage.release_sqlite_storage(workflow_storage)
