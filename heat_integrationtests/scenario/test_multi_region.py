#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from heat_integrationtests.scenario import scenario_base

TEST_REMOTE_REGION_TEMPLATE = '''
heat_template_version: 2015-04-30
description: Template for remote stack in Multi-Region test
parameters:
  value:
    type: string
resources:
  string:
    type: OS::Heat::TestResource
    properties:
        value: { get_param: value}
outputs:
  value:
    value: { get_attr: [string, output] }
'''

TEST_REMOTE_REGION_FAIL_TEMPLATE = '''
heat_template_version: 2015-04-30
description: Template for failing remote stack in Multi-Region test
parameters:
  value:
    type: string
resources:
  string:
    type: OS::Heat::TestResource
    properties:
        fail: True
        value: { get_param: value}
outputs:
  value:
    value: { get_attr: [string, output] }
'''


class MultiRegionTest(scenario_base.ScenarioTestsBase):
    """Class is responsible for testing multi region deployments."""
    def setUp(self):
        super(MultiRegionTest, self).setUp()
        self.stack_name = self._stack_rand_name()

    def _wait_for_remote_stacks(self, sid, remote_stacks={}, **kwargs):
        """Wait until all given remote stacks have the desired status."""
        for stack_name, stack_status in remote_stacks.items():
            self._wait_for_resource_status(
                sid, stack_name, stack_status, **kwargs)

    def check_stack_output(self, stack, output_key, expected_value):
        """Check the stack output.

        Compare the output with the given key to the expected value.
        """
        stack_output = self._stack_output(stack, output_key)['value']
        self.assertEqual(expected_value, stack_output)

    def check_stack_status(self, stack, expected_status):
        self.assertEqual(expected_status, stack.stack_status)

    def test_multi_region_stack(self):
        """Test the creation of remote stacks in multiple regions.

        Verify that for a stack containing multiple remote stacks:
            1. All remote stacks are created.
            2. The outputs of all remote stacks are passed to the parent stack.
            3. Deletion of the parent stack deletes all remote stacks.
            4. A failure in one of the remote stacks causes the parent stack to
               fail, too.
        """
        files = {
            'test_remote_region_1.yaml': TEST_REMOTE_REGION_TEMPLATE,
            'test_remote_region_2.yaml': TEST_REMOTE_REGION_TEMPLATE,
        }

        stack_identifier = self.launch_stack(
            stack_name=self.stack_name,
            template_name='test_multi_region.yaml',
            parameters={},
            files=files,
            expected_status=None
        )

        self._wait_for_remote_stacks(stack_identifier, {
            'stack_one': 'CREATE_COMPLETE',
            'stack_two': 'CREATE_COMPLETE',
        })
        stack = self.client.stacks.get(stack_identifier)

        self.check_stack_status(stack, 'CREATE_COMPLETE')
        self.check_stack_output(stack, 'stack_one_outputs', 'test1')
        self.check_stack_output(stack, 'stack_two_outputs', 'test2')

        self.client.stacks.delete(stack_identifier)

        self._wait_for_remote_stacks(stack_identifier, {
            'stack_one': 'DELETE_COMPLETE',
            'stack_two': 'DELETE_COMPLETE',
        }, success_on_not_found=True)
        self._wait_for_stack_status(stack_identifier, 'DELETE_COMPLETE')

        files['test_remote_region_2.yaml'] = TEST_REMOTE_REGION_FAIL_TEMPLATE

        stack_identifier = self.launch_stack(
            stack_name=self.stack_name,
            template_name='test_multi_region.yaml',
            parameters={},
            files=files,
            expected_status=None
        )

        self._wait_for_remote_stacks(stack_identifier, {
            'stack_one': 'CREATE_COMPLETE',
            'stack_two': 'CREATE_FAILED',
        })
        stack = self.client.stacks.get(stack_identifier)

        self.check_stack_status(stack, 'CREATE_FAILED')
