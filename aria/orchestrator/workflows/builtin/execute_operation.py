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

"""
Builtin execute_operation workflow
"""

from ..api.task import OperationTask
from ... import workflow


@workflow
def execute_operation(
        ctx,
        graph,
        operation,
        operation_kwargs,
        allow_kwargs_override,
        run_by_dependency_order,
        type_names,
        node_ids,
        node_instance_ids,
        **kwargs):
    """
    The execute_operation workflow

    :param WorkflowContext workflow_context: the workflow context
    :param TaskGraph graph: the graph which will describe the workflow.
    :param basestring operation: the operation name to execute
    :param dict operation_kwargs:
    :param bool allow_kwargs_override:
    :param bool run_by_dependency_order:
    :param type_names:
    :param node_ids:
    :param node_instance_ids:
    :param kwargs:
    :return:
    """
    subgraphs = {}
    # filtering node instances
    filtered_node_instances = list(_filter_node_instances(
        context=ctx,
        node_ids=node_ids,
        node_instance_ids=node_instance_ids,
        type_names=type_names))

    if run_by_dependency_order:
        filtered_node_instances_ids = set(node_instance.id
                                          for node_instance in filtered_node_instances)
        for node_instance in ctx.node_instances:
            if node_instance.id not in filtered_node_instances_ids:
                subgraphs[node_instance.id] = ctx.task_graph(
                    name='execute_operation_stub_{0}'.format(node_instance.id))

    # registering actual tasks to sequences
    for node_instance in filtered_node_instances:
        graph.add_tasks(
            _create_node_instance_task(
                node_instance=node_instance,
                operation=operation,
                operation_kwargs=operation_kwargs,
                allow_kwargs_override=allow_kwargs_override
            )
        )

    for _, node_instance_sub_workflow in subgraphs.items():
        graph.add_tasks(node_instance_sub_workflow)

    # adding tasks dependencies if required
    if run_by_dependency_order:
        for node_instance in ctx.node_instances:
            for relationship_instance in node_instance.relationship_instances:
                graph.add_dependency(source_task=subgraphs[node_instance.id],
                                     after=[subgraphs[relationship_instance.target_id]])


def _filter_node_instances(context, node_ids=(), node_instance_ids=(), type_names=()):
    def _is_node_by_id(node_id):
        return not node_ids or node_id in node_ids

    def _is_node_instance_by_id(node_instance_id):
        return not node_instance_ids or node_instance_id in node_instance_ids

    def _is_node_by_type(node_type_hierarchy):
        return not type_names or node_type_hierarchy in type_names

    for node_instance in context.node_instances:
        if all((_is_node_by_id(node_instance.node.id),
                _is_node_instance_by_id(node_instance.id),
                _is_node_by_type(node_instance.node.type_hierarchy))):
            yield node_instance


def _create_node_instance_task(
        node_instance,
        operation,
        operation_kwargs,
        allow_kwargs_override):
    """
    A workflow which executes a single operation
    :param node_instance: the node instance to install
    :param basestring operation: the operation name
    :param dict operation_kwargs:
    :param bool allow_kwargs_override:
    :return:
    """

    if allow_kwargs_override is not None:
        operation_kwargs['allow_kwargs_override'] = allow_kwargs_override

    return OperationTask.node_instance(
        instance=node_instance,
        name=operation,
        inputs=operation_kwargs)
