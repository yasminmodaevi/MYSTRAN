from spiffworkflow.bpmn.parser.BpmnParser import BpmnParser
from spiffworkflow.executable_data import ExecutableData
from spiffworkflow.workflow import Workflow
from spiffworkflow.specs import WorkflowSpec

class WorkflowService:
    @staticmethod
    def create_workflow_spec(bpmn_xml_content: str):
        parser = BpmnParser()
        # Create a spec from the XML content
        # Note: SpiffWorkflow implementation varies by version, this is a standard pattern
        spec = parser.parse_string(bpmn_xml_content)
        return spec

    @staticmethod
    def start_process(spec: WorkflowSpec, data: dict = None):
        workflow = Workflow(spec)
        if data:
            workflow.data.update(data)
        return workflow

    @staticmethod
    def get_ready_tasks(workflow: Workflow):
        return workflow.get_ready_tasks()
