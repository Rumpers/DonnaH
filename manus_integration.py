import os
import logging
import json
import asyncio
import sys
from datetime import datetime
import re
import random

# Add OpenManus to the Python path
sys.path.append('./OpenManus')

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Track if we're using the real OpenManus or the mock version
using_real_openmanus = False

# OpenManus implementation for local development
# This is a mock implementation that simulates the behavior of the OpenManus API
class OpenManus:
    def __init__(self):
        self.api_key = os.environ.get("MANUS_API_KEY", "demo_key")
        self.initialized = False
        
        # Sample memory types
        self.memory_types = ["project", "person", "event", "document", "idea", "task"]
        
        # Sample categories for documents
        self.document_categories = [
            "Financial", "Legal", "Technical", "Marketing", 
            "HR", "Research", "Project Plan", "Meeting Notes"
        ]
    
    def initialize(self):
        """Initialize the OpenManus framework."""
        logger.info("Initializing OpenManus framework (local implementation)")
        self.initialized = True
        return True
    
    def process_message(self, user, message, current_state):
        """Process a message using natural language understanding."""
        if not self.initialized:
            return "Sorry, I'm having trouble connecting to my brain. Please try again later."
        
        # Sample responses based on keywords in the message
        email_patterns = ["email", "inbox", "message", "send", "mail"]
        calendar_patterns = ["calendar", "schedule", "meeting", "appointment", "event"]
        drive_patterns = ["drive", "document", "file", "folder", "share"]
        memory_patterns = ["remember", "recall", "memorize", "store", "what do you know"]
        
        message_lower = message.lower()
        
        # Check for greetings
        if re.search(r'\b(hi|hello|hey)\b', message_lower):
            return f"Hello! I'm your executive assistant. How can I help you today?"
        
        # Email-related queries
        if any(pattern in message_lower for pattern in email_patterns):
            if "unread" in message_lower:
                return "You have 3 unread emails. The most recent one is from John Smith about 'Project Update'."
            elif "send" in message_lower:
                match = re.search(r'send .+ to (\w+@\w+\.\w+)', message_lower)
                recipient = match.group(1) if match else "the recipient"
                return f"I've prepared an email to {recipient}. Would you like to review it before sending?"
            else:
                return "I can help you manage your emails. Would you like me to check your inbox or help you compose a message?"
        
        # Calendar-related queries
        elif any(pattern in message_lower for pattern in calendar_patterns):
            if "today" in message_lower:
                return "You have 2 meetings scheduled for today: Team standup at 10:00 AM and Client call at 2:30 PM."
            elif "schedule" in message_lower or "create" in message_lower:
                return "I can help you schedule a new meeting. What's the date, time, and who should attend?"
            else:
                return "I can help you manage your calendar. Would you like to see today's schedule or create a new event?"
        
        # Drive-related queries
        elif any(pattern in message_lower for pattern in drive_patterns):
            if "recent" in message_lower:
                return "Your recent documents include: 'Q1 Report.pdf', 'Marketing Strategy.docx', and 'Team Structure.xlsx'."
            elif "share" in message_lower:
                return "Which document would you like to share, and with whom?"
            else:
                return "I can help you manage your Google Drive files. What would you like to do?"
        
        # Memory-related queries
        elif any(pattern in message_lower for pattern in memory_patterns):
            if "project" in message_lower:
                return "I found information about several projects in my memory. The most recent one is 'Website Redesign' which started last month."
            elif "person" in message_lower or "contact" in message_lower:
                return "I found several contacts in my memory. Would you like me to provide details about a specific person?"
            else:
                return "I can help you recall information from my memory. What specific information are you looking for?"
        
        # Default response
        else:
            return "I'm here to help you manage emails, calendar, drive, and other tasks. How can I assist you today?"
    
    def generate_document_summary(self, document_text):
        """Generate a summary of a document."""
        if not self.initialized:
            return "Unable to generate summary: Service unavailable."
        
        # For demonstration, generate a simple summary based on document length
        words = document_text.split()
        word_count = len(words)
        
        if word_count < 50:
            return document_text  # Short document, return as is
        
        # Extract some sentences for the summary
        sentences = re.split(r'(?<=[.!?])\s+', document_text)
        summary_length = min(5, len(sentences))
        
        summary = " ".join(sentences[:summary_length])
        return f"{summary}\n\nThis document contains {word_count} words covering topics related to business operations and strategic planning."
    
    def extract_memories(self, user, conversation_text):
        """Extract potential memory entries from conversation text."""
        if not self.initialized:
            return []
        
        # Sample memory extraction
        memories = []
        
        # Look for potential people mentions
        people_matches = re.finditer(r'(?:([A-Z][a-z]+ [A-Z][a-z]+)|(?:([A-Z][a-z]+)))', conversation_text)
        for match in people_matches:
            name = match.group(0)
            if random.random() > 0.7:  # Only extract some names to avoid too many
                memories.append({
                    "type": "person",
                    "title": name,
                    "content": f"Person mentioned in conversation on {datetime.now().strftime('%Y-%m-%d')}."
                })
        
        # Look for potential projects
        project_matches = re.finditer(r'(?:project|initiative|plan)s? (?:(?:called|named) )?["\']?([A-Z][a-zA-Z0-9 ]+)["\']?', 
                                      conversation_text, re.IGNORECASE)
        for match in project_matches:
            project_name = match.group(1)
            memories.append({
                "type": "project",
                "title": project_name,
                "content": f"Project mentioned in conversation on {datetime.now().strftime('%Y-%m-%d')}."
            })
        
        # Look for potential dates/events
        date_matches = re.finditer(r'(?:meeting|call|event|conference)(?:s)? on ([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?(?:,? \d{4})?)', 
                                  conversation_text, re.IGNORECASE)
        for match in date_matches:
            event_date = match.group(1)
            memory_content = conversation_text[max(0, match.start() - 50):min(len(conversation_text), match.end() + 50)]
            memories.append({
                "type": "event",
                "title": f"Event on {event_date}",
                "content": memory_content
            })
        
        return memories
    
    def analyze_email(self, email_content):
        """Analyze email content to extract important information."""
        if not self.initialized:
            return {}
        
        # Simple email analysis
        analysis = {
            "importance": "medium",
            "category": "general",
            "action_required": False,
            "entities": []
        }
        
        # Check for urgency keywords
        urgency_keywords = ["urgent", "asap", "immediately", "emergency", "deadline"]
        if any(keyword in email_content.lower() for keyword in urgency_keywords):
            analysis["importance"] = "high"
            analysis["action_required"] = True
        
        # Extract potential dates
        dates = re.findall(r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', 
                          email_content)
        if dates:
            analysis["dates"] = dates
        
        # Extract potential people/names
        names = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', email_content)
        if names:
            analysis["entities"] = [{"type": "person", "name": name} for name in names]
        
        return analysis
    
    def analyze_calendar_event(self, event_details):
        """Analyze calendar event to extract important information."""
        if not self.initialized:
            return {}
        
        # Simple event analysis
        analysis = {
            "importance": "medium",
            "category": "meeting",
            "preparation_required": False,
            "participants": []
        }
        
        event_summary = event_details.get("summary", "").lower()
        event_description = event_details.get("description", "").lower()
        
        # Check for importance
        if any(keyword in event_summary for keyword in ["important", "urgent", "critical"]):
            analysis["importance"] = "high"
        
        # Check for preparation
        prep_keywords = ["prepare", "presentation", "review", "bring", "discuss"]
        if any(keyword in event_description for keyword in prep_keywords):
            analysis["preparation_required"] = True
            prep_items = []
            for keyword in prep_keywords:
                if keyword in event_description:
                    # Extract context around the keyword
                    pos = event_description.find(keyword)
                    context = event_description[max(0, pos-20):min(len(event_description), pos+50)]
                    prep_items.append(context)
            analysis["preparation_items"] = prep_items
        
        # Extract participants from attendees if available
        if "attendees" in event_details:
            analysis["participants"] = [
                {"email": attendee.get("email"), "name": attendee.get("displayName")}
                for attendee in event_details["attendees"]
            ]
        
        return analysis
    
    def generate_email_response(self, email_content, response_type="draft"):
        """Generate an email response."""
        if not self.initialized:
            return "Unable to generate email response: Service unavailable."
        
        # Extract subject if available
        subject_match = re.search(r'Subject: (.*)', email_content)
        subject = subject_match.group(1) if subject_match else "your email"
        
        # Generate appropriate response based on type
        if response_type == "accept":
            return f"Thank you for {subject}. I'm pleased to accept and look forward to working with you on this."
        elif response_type == "decline":
            return f"Thank you for {subject}. Unfortunately, I won't be able to participate at this time due to prior commitments."
        elif response_type == "request_info":
            return f"Thank you for {subject}. Could you please provide additional information about the timelines and requirements?"
        else:  # default draft
            return f"Thank you for {subject}. I've reviewed the information you shared and will get back to you with my thoughts soon."
    
    def categorize_document_content(self, document_text):
        """Categorize document content based on its text."""
        if not self.initialized:
            return "Unknown"
        
        # Sample categorization based on keywords
        financial_keywords = ["budget", "expense", "revenue", "financial", "cost", "profit", "loss"]
        legal_keywords = ["agreement", "contract", "legal", "compliance", "regulation", "law", "policy"]
        technical_keywords = ["software", "hardware", "system", "technical", "technology", "implementation"]
        marketing_keywords = ["marketing", "campaign", "brand", "customer", "market", "advertising"]
        
        text_lower = document_text.lower()
        
        # Count keyword occurrences for each category
        counts = {
            "Financial": sum(1 for keyword in financial_keywords if keyword in text_lower),
            "Legal": sum(1 for keyword in legal_keywords if keyword in text_lower),
            "Technical": sum(1 for keyword in technical_keywords if keyword in text_lower),
            "Marketing": sum(1 for keyword in marketing_keywords if keyword in text_lower)
        }
        
        # Find the category with the most keyword matches
        if max(counts.values()) > 0:
            category = max(counts.items(), key=lambda x: x[1])[0]
        else:
            # If no clear category, use one of the predefined categories
            category = random.choice(self.document_categories)
        
        return category

# Real OpenManus agent using OpenAI API directly
class RealOpenManus:
    def __init__(self):
        self.api_key = None
        self.initialized = False
        self.system_prompt = """
        You are an advanced assistant named OpenManus. You specialize in helping users manage their emails, 
        calendar events, documents, and personal information. Your responses should be helpful, 
        informative, and accurate. When asked to format responses as JSON, always do so correctly.
        """
    
    def initialize(self):
        """Initialize the OpenAI-based implementation."""
        try:
            # Check for OpenAI API key
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                logger.warning("OpenAI API key not found. Integration will have limited functionality.")
                return False
            
            # Try to import OpenAI package
            try:
                import openai
                openai.api_key = self.api_key
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("Successfully initialized OpenAI client")
                self.initialized = True
                return True
            except ImportError:
                logger.error("Failed to import OpenAI package")
                return False
        except Exception as e:
            logger.error(f"Error initializing OpenAI integration: {e}")
            return False
    
    async def _async_run(self, prompt, system_prompt=None):
        """Run the OpenAI API with a prompt asynchronously."""
        if not self.initialized:
            return {"response": "OpenAI integration is not initialized properly.", "error": True}
        
        try:
            import openai
            
            # Set up the messages for the chat completion
            messages = [
                {"role": "system", "content": system_prompt or self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # Call the OpenAI API
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract the response content
            if response.choices and len(response.choices) > 0:
                return {"response": response.choices[0].message.content, "error": False}
            
            return {"response": "No response generated.", "error": True}
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return {"response": f"Error: {str(e)}", "error": True}
    
    def process_message(self, user, message, current_state):
        """Process a message using natural language understanding."""
        try:
            # Format context information for the prompt
            context = ""
            if current_state:
                context = f"Context: {json.dumps(current_state)}\n\n"
            
            # Create the prompt with user and context information
            prompt = f"{context}User {user.username}: {message}"
            
            # Run the agent in the event loop
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._async_run(prompt))
            
            if result["error"]:
                return result["response"]
            
            # Format the response as expected by the caller
            response = {
                "message": result["response"],
                "intents": [],  # We don't have explicit intents from OpenManus
                "entities": {},  # We don't have explicit entities from OpenManus
                "action": {"action": "none", "parameters": {}},
                "confidence": 0.9
            }
            
            return response
        except Exception as e:
            logger.error(f"Error processing message with real OpenManus: {e}")
            return "I encountered an error processing your request."
    
    def generate_document_summary(self, document_text):
        """Generate a summary of a document."""
        try:
            # Create a prompt for document summarization
            prompt = f"Please summarize the following document:\n\n{document_text[:3000]}..."
            
            # Run the agent in the event loop
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._async_run(prompt))
            
            if result["error"]:
                return "Failed to generate document summary."
            
            return result["response"]
        except Exception as e:
            logger.error(f"Error generating document summary with real OpenManus: {e}")
            return "Failed to generate document summary."
    
    def extract_memories(self, user, conversation_text):
        """Extract potential memory entries from conversation text."""
        try:
            # Create a prompt for memory extraction
            prompt = (
                f"Extract key information from this conversation that should be remembered as memory entries. "
                f"Format your response as a JSON array with objects containing 'type', 'title', and 'content' fields. "
                f"Valid types are: project, person, event, document, idea, task.\n\n"
                f"Conversation:\n{conversation_text}"
            )
            
            # Run the agent in the event loop
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._async_run(prompt))
            
            if result["error"]:
                return []
            
            # Try to extract JSON from the response
            try:
                response = result["response"]
                start_idx = response.find('[')
                end_idx = response.rfind(']') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    memories = json.loads(json_str)
                    return memories
                return []
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response for memory extraction")
                return []
        except Exception as e:
            logger.error(f"Error extracting memories with real OpenManus: {e}")
            return []
    
    def analyze_email(self, email_content):
        """Analyze email content to extract important information."""
        try:
            # Create a prompt for email analysis
            prompt = (
                f"Analyze this email and extract important information. "
                f"Format your response as a JSON object with 'importance', 'category', 'action_required', "
                f"'dates', and 'entities' fields.\n\n"
                f"Email:\n{email_content}"
            )
            
            # Run the agent in the event loop
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._async_run(prompt))
            
            if result["error"]:
                return {"importance": "medium", "category": "general", "action_required": False}
            
            # Try to extract JSON from the response
            try:
                response = result["response"]
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    analysis = json.loads(json_str)
                    return analysis
                return {"importance": "medium", "category": "general", "action_required": False}
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response for email analysis")
                return {"importance": "medium", "category": "general", "action_required": False}
        except Exception as e:
            logger.error(f"Error analyzing email with real OpenManus: {e}")
            return {"importance": "medium", "category": "general", "action_required": False}
    
    def analyze_calendar_event(self, event_details):
        """Analyze calendar event to extract important information."""
        try:
            # Format the event details as a JSON string
            event_json = json.dumps(event_details, indent=2)
            
            # Create a prompt for calendar event analysis
            prompt = (
                f"Analyze this calendar event and extract important information. "
                f"Format your response as a JSON object with 'importance', 'category', 'preparation_required', "
                f"and 'participants' fields.\n\n"
                f"Event:\n{event_json}"
            )
            
            # Run the agent in the event loop
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._async_run(prompt))
            
            if result["error"]:
                return {"importance": "medium", "category": "meeting", "preparation_required": False}
            
            # Try to extract JSON from the response
            try:
                response = result["response"]
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    analysis = json.loads(json_str)
                    return analysis
                return {"importance": "medium", "category": "meeting", "preparation_required": False}
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response for calendar event analysis")
                return {"importance": "medium", "category": "meeting", "preparation_required": False}
        except Exception as e:
            logger.error(f"Error analyzing calendar event with real OpenManus: {e}")
            return {"importance": "medium", "category": "meeting", "preparation_required": False}
    
    def generate_email_response(self, email_content, response_type="draft"):
        """Generate an email response."""
        try:
            # Create a prompt for email response generation
            prompt = (
                f"Generate a {response_type} email response to the following email content. "
                f"The response should be formatted as a proper email with greeting and closing.\n\n"
                f"Email content:\n{email_content}"
            )
            
            # Run the agent in the event loop
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._async_run(prompt))
            
            if result["error"]:
                return "Failed to generate email response."
            
            return result["response"]
        except Exception as e:
            logger.error(f"Error generating email response with real OpenManus: {e}")
            return "Failed to generate email response."
    
    def categorize_document_content(self, document_text):
        """Categorize document content based on its text."""
        try:
            # Create a prompt for document categorization
            prompt = (
                f"Categorize this document content. Format your response as a JSON object with "
                f"'category' and 'confidence' fields.\n\n"
                f"Document excerpt:\n{document_text[:1000]}..."
            )
            
            # Run the agent in the event loop
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self._async_run(prompt))
            
            if result["error"]:
                return "Unknown"
            
            # Try to extract JSON from the response
            try:
                response = result["response"]
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    categorization = json.loads(json_str)
                    return categorization.get("category", "Unknown")
                return "Unknown"
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response for document categorization")
                return "Unknown"
        except Exception as e:
            logger.error(f"Error categorizing document with real OpenManus: {e}")
            return "Unknown"

# Create singleton instances for both implementations
_mock_openmanus = OpenManus()
_real_openmanus = RealOpenManus()
_current_openmanus = None

# Module functions that use the appropriate implementation
def initialize_manus():
    """Initialize the OpenManus framework."""
    global _current_openmanus, using_real_openmanus
    
    # First try to initialize the real OpenManus
    try:
        if _real_openmanus.initialize():
            _current_openmanus = _real_openmanus
            using_real_openmanus = True
            logger.info("Successfully initialized real OpenManus")
            return True
    except Exception as e:
        logger.error(f"Error initializing real OpenManus: {e}")
    
    # Fall back to the mock implementation
    logger.warning("Falling back to mock OpenManus implementation")
    _mock_openmanus.initialize()
    _current_openmanus = _mock_openmanus
    using_real_openmanus = False
    
    return True

def process_message(user, message, current_state):
    """Process a message using the OpenManus framework."""
    global _current_openmanus
    
    if _current_openmanus is None:
        initialize_manus()
    
    return _current_openmanus.process_message(user, message, current_state)

def generate_document_summary(document_text):
    """Generate a summary of a document using OpenManus."""
    global _current_openmanus
    
    if _current_openmanus is None:
        initialize_manus()
    
    return _current_openmanus.generate_document_summary(document_text)

def extract_memories(user, conversation_text):
    """Extract potential memory entries from conversation text."""
    global _current_openmanus
    
    if _current_openmanus is None:
        initialize_manus()
    
    return _current_openmanus.extract_memories(user, conversation_text)

def analyze_email(email_content):
    """Analyze email content to extract important information."""
    global _current_openmanus
    
    if _current_openmanus is None:
        initialize_manus()
    
    return _current_openmanus.analyze_email(email_content)

def analyze_calendar_event(event_details):
    """Analyze calendar event to extract important information."""
    global _current_openmanus
    
    if _current_openmanus is None:
        initialize_manus()
    
    return _current_openmanus.analyze_calendar_event(event_details)

def generate_email_response(email_content, response_type="draft"):
    """Generate an email response based on the content of a received email."""
    global _current_openmanus
    
    if _current_openmanus is None:
        initialize_manus()
    
    return _current_openmanus.generate_email_response(email_content, response_type)

def categorize_document_content(document_text):
    """Categorize document content based on its text."""
    global _current_openmanus
    
    if _current_openmanus is None:
        initialize_manus()
    
    return _current_openmanus.categorize_document_content(document_text)
