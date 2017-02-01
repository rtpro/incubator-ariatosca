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

import aria


def operation_context_to_dict(context):
    context_cls = context.__class__
    context_dict = {
        'name': context.name,
        'deployment_id': context._deployment_id,
        'task_id': context._task_id,
        'actor_id': context._actor_id,
        'workdir': context._workdir
    }
    if context.model:
        model = context.model
        context_dict['model_storage'] = {
            'api_cls': model.api,
            'driver_kwargs': model._driver_kwargs,
        }
    else:
        context_dict['model_storage'] = None
    if context.resource:
        resource = context.resource
        context_dict['resource_storage'] = {
            'api_cls': resource.api,
            'driver_kwargs': resource._driver_kwargs
        }
    else:
        context_dict['resource_storage'] = None
    return {
        'context_cls': context_cls,
        'context': context_dict
    }


def operation_context_from_dict(context_dict):
    context_cls = context_dict['context_cls']
    context = context_dict['context']

    model_storage = context['model_storage']
    if model_storage:
        api_cls = model_storage['api_cls']
        driver_kwargs = model_storage['driver_kwargs']
        context['model_storage'] = aria.application_model_storage(
            api_cls, driver_kwargs=driver_kwargs)

    resource_storage = context['resource_storage']
    if resource_storage:
        api_cls = resource_storage['api_cls']
        driver_kwargs = resource_storage['driver_kwargs']
        context['resource_storage'] = aria.application_resource_storage(
             api=api_cls, driver_kwargs=driver_kwargs)

    return context_cls(**context)
