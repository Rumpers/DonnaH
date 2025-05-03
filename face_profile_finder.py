"""
Face profile finder module for the assistant.
Uses OpenAI vision to identify people in photos and find profile pictures.
"""

import os
import json
import base64
import logging
import requests
from io import BytesIO
import time
from PIL import Image
from app import db
from models import User, MemoryEntry, FaceImage
# Access OpenAI through the manus_integration module
import manus_integration
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def encode_image_to_base64(image_path):
    """Convert an image to base64 encoding."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image to base64: {e}")
        return None

def save_image_to_file(image_data, filename, directory="uploads/profiles"):
    """Save image data to a file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        filepath = os.path.join(directory, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        return filepath
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return None

def extract_faces_from_image(image_path, context=None):
    """
    Use OpenAI vision to identify faces in an image.
    
    Args:
        image_path: Path to the image file
        context: Optional context about who we're looking for
        
    Returns:
        List of faces found with descriptions and positions
    """
    try:
        # Encode the image
        base64_image = encode_image_to_base64(image_path)
        if not base64_image:
            return []
        
        # Create the prompt based on context
        if context:
            prompt = f"Please identify all people in this image. I'm specifically looking for {context}. For each person, provide their position (top-left, center, etc.) and a brief description of their appearance. Output in JSON format with keys: faces (array of objects with position, description)."
        else:
            prompt = "Please identify all people in this image. For each person, provide their position (top-left, center, etc.) and a brief description of their appearance. Output in JSON format with keys: faces (array of objects with position, description)."
        
        # Call OpenAI API with the image through manus_integration
        response = manus_integration.openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        return result.get('faces', [])
    except Exception as e:
        logger.error(f"Error extracting faces from image: {e}")
        return []

def find_profile_picture_online(name, company=None):
    """
    Search online for a profile picture of a person.
    This is a simplified version that would be expanded with actual search APIs.
    
    Args:
        name: Name of the person
        company: Optional company name for better search
        
    Returns:
        URL to the profile image if found, None otherwise
    """
    try:
        # This would be enhanced with actual API calls to Google/Bing Search or LinkedIn
        # For now, return None as we don't have search API credentials
        logger.info(f"Would search for profile picture of {name} from {company or 'any company'}")
        return None
    except Exception as e:
        logger.error(f"Error finding profile picture: {e}")
        return None

def add_profile_image_from_business_card(memory_entry_id, image_path):
    """
    When a business card is processed, extract the person's face and save it.
    
    Args:
        memory_entry_id: ID of the memory entry (contact)
        image_path: Path to the business card image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the memory entry
        memory_entry = MemoryEntry.query.get(memory_entry_id)
        if not memory_entry:
            logger.error(f"Memory entry {memory_entry_id} not found")
            return False
        
        # Load the memory entry content
        content = json.loads(memory_entry.content)
        name = content.get('name', 'Unknown')
        
        # Extract faces from the image
        faces = extract_faces_from_image(image_path, context=name)
        
        if not faces:
            logger.info(f"No faces found in business card for {name}")
            return False
        
        # Use the first face found (likely the only one on a business card)
        face = faces[0]
        
        # Create a face image entry
        face_image = FaceImage(
            memory_entry_id=memory_entry_id,
            image_path=image_path,
            is_profile=True,  # Make it the profile image
            source='business_card',
            face_encoding=json.dumps(face)  # Save the face description
        )
        
        db.session.add(face_image)
        db.session.commit()
        
        logger.info(f"Added profile image for {name} from business card")
        return True
        
    except Exception as e:
        logger.error(f"Error adding profile image from business card: {e}")
        db.session.rollback()
        return False

def identify_person_in_photo(user_id, image_path, query_name=None):
    """
    Identify a person in a photo based on their name.
    
    Args:
        user_id: ID of the user
        image_path: Path to the photo
        query_name: Name of the person to look for
        
    Returns:
        Dictionary with identification results
    """
    try:
        # Extract all faces from the image
        faces = extract_faces_from_image(image_path, context=query_name)
        
        if not faces:
            return {
                "success": False,
                "message": "No faces found in the image."
            }
            
        # If no specific name provided, just return all faces found
        if not query_name:
            return {
                "success": True,
                "message": f"Found {len(faces)} faces in the image.",
                "faces": faces
            }
            
        # If a name is provided, try to match with memory entries
        memory_entries = MemoryEntry.query.filter_by(
            user_id=user_id,
            entry_type='contact'
        ).all()
        
        possible_matches = []
        
        for entry in memory_entries:
            content = json.loads(entry.content)
            name = content.get('name', '')
            
            # Simple name matching - would be enhanced with actual face recognition
            if query_name.lower() in name.lower():
                possible_matches.append({
                    "memory_id": entry.id,
                    "name": name,
                    "faces": faces
                })
        
        if possible_matches:
            return {
                "success": True,
                "message": f"Found potential matches for {query_name}.",
                "matches": possible_matches
            }
        else:
            return {
                "success": False,
                "message": f"No matches found for {query_name} in your contacts."
            }
    
    except Exception as e:
        logger.error(f"Error identifying person in photo: {e}")
        return {
            "success": False,
            "message": f"Error processing image: {str(e)}"
        }

def save_identified_person(memory_entry_id, image_path, face_position):
    """
    Save an identified person's face from a group photo.
    
    Args:
        memory_entry_id: ID of the memory entry (contact)
        image_path: Path to the photo
        face_position: Description of face position in the image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create a face image entry
        face_image = FaceImage(
            memory_entry_id=memory_entry_id,
            image_path=image_path,
            is_profile=False,  # Not a profile image
            source='group_photo',
            face_encoding=json.dumps({"position": face_position})
        )
        
        db.session.add(face_image)
        db.session.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving identified person: {e}")
        db.session.rollback()
        return False