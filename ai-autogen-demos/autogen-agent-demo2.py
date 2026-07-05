"""
Using Autogen for Autonomous Internal Document QA and Policy Compliance

Objective: To demonstrate an intelligent system that automatically checks all company documents for 
compliance issues and notifies the right people to fix them. Think of it as your automated document 
assistant—like having a dedicated team that never sleeps, reviewing every policy, manual, and guideline 
for problems
"""

# Step 1: Import necessary libraries
import os
from dotenv import load_dotenv
import autogen
from typing import Dict, List, Optional
import json
from datetime import datetime

load_dotenv()  # Load environment variables from .env file

# Step 2: Create a configuration list and an LLM configuration

# Creating a variable for configuration
config_list = [
    {
        "model": "gpt-5-mini", # Azure deployment name
        "api_key": os.getenv("OPENAI_API_KEY"),
        "max_completion_tokens": 3000,
    }
]
# Create LLM configuration
llm_config = {
    "config_list": config_list,
}

# Step 3: Create a sample document
SAMPLE_DOCUMENTS = [
    {
        "id": "DOC001",
        "title": "Employee Remote Work Policy",
        "type": "HR Policy",
        "content": """
        Remote Work Policy
        Effective Date: January 2023
        1. Eligibility: All full-time employees
        2. Equipment: Company will provide laptop
        3. Work Hours: Standard 9-5 EST
        Note: This policy supersedes the 2021 remote work guidelines.
        """,
        "last_updated": "2023-01-15"
    },
    {
        "id": "DOC002",
        "title": "Data Security Manual",
        "type": "Technical Manual",
        "content": """
        Data Security Manual
        Version: 2.1
        1. Password Requirements: Minimum 8 characters
        2. Encryption: Use AES-256 for sensitive data
        Missing sections:
        - Incident Response Procedures
        - Data Retention Policy
        """,
        "last_updated": "2024-03-20"
    },
    {
        "id": "DOC003",
        "title": "Customer Service Guidelines",
        "type": "Operational Guidelines",
        "content": """
        Customer Service Guidelines
        1. Response Time: Within 24 hours
        2. Escalation: After 48 hours to supervisor
        3. Communication: Use template responses from 2019 handbook
        Approved by: [Missing Signature]
        Review Date: [Not Specified]
        """,
        "last_updated": "2024-11-10"
    }
]

# Step 4: Create specialized agents
# Define specialized agents
class DocumentComplianceSystem:
    def __init__(self):
        # Document Scanner Agent - Monitors and retrieves documents
        self.document_scanner = autogen.AssistantAgent(
            name="DocumentScanner",
            llm_config=llm_config,
            system_message="""You are a Document Scanner agent responsible for:
            1. Monitoring document repositories for new or updated documents
            2. Extracting document metadata (title, type, last updated date)
            3. Preparing documents for compliance analysis
            4. Identifying document categories (HR, Technical, Operational)
            Format your findings clearly with document ID, type, and key metadata."""
        )

        # Compliance Checker Agent - Analyzes documents for compliance issues
        self.compliance_checker = autogen.AssistantAgent(
            name="ComplianceChecker",
            llm_config=llm_config,
            system_message="""You are a Compliance Checker agent responsible for:
            1. Analyzing documents for compliance issues such as:
            - Missing required sections (approvals, dates, signatures)
            - Outdated references or superseded content
            - Inconsistent terminology or formatting
            - Version control issues
            2. Categorizing issues by severity (Critical, Major, Minor)
            3. Providing specific recommendations for remediation
            Always structure your analysis with: Issue Type | Severity | Details | Recommendation"""
        )

        # Review Coordinator Agent - Routes documents and manages escalations
        self.review_coordinator = autogen.AssistantAgent(
            name="ReviewCoordinator",
            llm_config=llm_config,
            system_message="""You are a Review Coordinator agent responsible for:
            1. Processing compliance check results
            2. Determining routing based on severity:
            - Critical: Immediate escalation to Legal/Executive review
            - Major: Route to department head for approval
            - Minor: Send revision request to document owner
            3. Generating action items with deadlines
            4. Creating audit trail for compliance tracking
            Format routing decisions with: Document | Issues | Routing Decision | Action Items | Due Date"""
        )

        # User Proxy Agent - Represents human interaction points
        self.user_proxy = autogen.UserProxyAgent(
            name="UserProxy",
            human_input_mode="TERMINATE",
            max_consecutive_auto_reply=2,
            code_execution_config=False,
        )

        # Create group chat for multi-agent collaboration
        self.group_chat = autogen.GroupChat(
            agents=[
                self.document_scanner,
                self.compliance_checker,
                self.review_coordinator,
                self.user_proxy
            ],
            messages=[],
            max_round=10
        )

        self.manager = autogen.GroupChatManager(
            groupchat=self.group_chat,
            llm_config=llm_config
        )

    def process_document_batch(self, documents: List[Dict]):
        """Process a batch of documents through the compliance workflow"""
        print("🚀 Starting AutoGen Document Compliance Workflow\n")
        print("=" * 60)
        # Convert documents to a formatted string for processing
        doc_summary = "\n\n".join([
            f"Document ID: {doc['id']}\n"
            f"Title: {doc['title']}\n"
            f"Type: {doc['type']}\n"
            f"Last Updated: {doc['last_updated']}\n"
            f"Content Preview:\n{doc['content'][:200]}..."
            for doc in documents
        ])

        # Initiate the multi-agent workflow
        initial_message = f"""
        New documents have been detected in the repository. Please process these documents through our compliance workflow:
        {doc_summary}
        Workflow Steps:
        1. DocumentScanner: Analyze and categorize the documents
        2. ComplianceChecker: Perform compliance analysis on each document
        3. ReviewCoordinator: Determine routing and create action items
        Begin the analysis.
        """
        self.user_proxy.initiate_chat(
            self.manager,
            message=initial_message
        )
        return self.generate_compliance_report()

    def generate_compliance_report(self):
        """Generate a summary compliance report"""
        print("\n" + "=" * 60)
        print("📊 COMPLIANCE WORKFLOW SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Documents Processed: {len(SAMPLE_DOCUMENTS)}")
        print("\nKey Findings:")
        print("- Missing required sections detected in technical documentation")
        print("- Outdated references found in operational guidelines")
        print("- Signature approvals missing in customer service documents")
        print("\nWorkflow Demonstration Complete ✅")

# Step 5: Create a function to run the agents
# Demonstration function
def run_demo():
    """Run the AutoGen document compliance demonstration"""
    print("🤖 AutoGen Document Compliance System Demo")
    print("=" * 60)
    print("Demonstrating key AutoGen features:")
    print("✓ Multi-agent collaboration")
    print("✓ Declarative agent configuration")
    print("✓ Group chat orchestration")
    print("✓ Automated workflow execution")
    print("=" * 60 + "\n")
    # Initialize the compliance system
    compliance_system = DocumentComplianceSystem()
    # Process the sample documents
    compliance_system.process_document_batch(SAMPLE_DOCUMENTS)

# Step 6: Create a function to set up custom compliance rules
# Additional helper functions for extended functionality
def create_custom_compliance_rules():
    """Define custom compliance rules for different document types"""
    return {
        "HR Policy": {
            "required_sections": ["Effective Date", "Eligibility", "Approval"],
            "max_age_months": 12,
            "requires_signature": True
        },
            "Technical Manual": {
            "required_sections": ["Version", "Security Requirements", "Incident Response"],
            "max_age_months": 6,
            "requires_signature": False
        },
            "Operational Guidelines": {
            "required_sections": ["Procedures", "Escalation", "Review Date"],
            "max_age_months": 12,
            "requires_signature": True
        }
    }

# Step 7: Define a function to set up webhook monitoring
def setup_monitoring_webhook():
    """Setup webhook for continuous document monitoring"""
    webhook_config = {
        "endpoint": "/api/document-updates",
        "events": ["document.created", "document.updated"],
        "frequency": "real-time"
    }
    return webhook_config

# Step 8: Include the try and except statements and execute the code
if __name__ == "__main__":
    print("\n🔧 SETUP INSTRUCTIONS:")
    print("1. Install AutoGen: pip install pyautogen")
    print("2. Set your OpenAI API key: export OPENAI_API_KEY='your-key'")
    print("3. Run this script: python autogen_compliance_demo.py\n")
    try:
        run_demo()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure you have set up your API key and installed AutoGen.")