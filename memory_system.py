import os
import logging
import json
import hashlib
import re
from datetime import datetime
from app import db
from models import MemoryEntry, Message

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Simple in-memory storage for development
memory_store = {}

def simple_embedding(text):
    """
    A very simple embedding function that just creates a hash of the text.
    This is NOT suitable for production but works for demonstration.
    """
    # Convert text to lowercase and remove punctuation for better matching
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    
    # Create a hash of the text
    hash_obj = hashlib.md5(text.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Convert the hash to a list of floats (simulated embedding)
    embedding = []
    for i in range(0, len(hash_hex), 2):
        if i < len(hash_hex) - 1:
            val = int(hash_hex[i:i+2], 16) / 255.0  # Normalize to 0-1
            embedding.append(val)
    
    return embedding

def initialize_memory_system():
    """Initialize the memory system with a simple in-memory store."""
    global memory_store
    
    try:
        # Initialize in-memory store
        memory_store = {}
        
        logger.info("Memory system initialized successfully (simple mode)")
        return True
    except Exception as e:
        logger.error(f"Error initializing memory system: {e}")
        return False

def add_memory(user, entry_type, title, content, metadata=None):
    """Add a new memory entry to the database and simple store."""
    try:
        # Create new memory entry
        metadata = metadata or {}
        
        # Generate vector embedding using simple function
        text_to_embed = f"{title} {content}"
        embedding = simple_embedding(text_to_embed)
        embedding_json = json.dumps(embedding)
        
        # Create database entry
        memory_entry = MemoryEntry(
            user_id=user.id,
            entry_type=entry_type,
            title=title,
            content=content,
            meta_data=metadata,  # Updated to match the renamed field
            vector_embedding=embedding_json,
            created_at=datetime.utcnow()
        )
        
        db.session.add(memory_entry)
        db.session.commit()
        
        # Add to simple memory store
        memory_key = f"memory_{memory_entry.id}"
        memory_store[memory_key] = {
            "user_id": str(user.id),
            "memory_id": str(memory_entry.id),
            "entry_type": entry_type,
            "title": title,
            "content": content,
            "embedding": embedding,
            "text": text_to_embed
        }
        
        return memory_entry
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        db.session.rollback()
        raise

def search_memory(user, query, limit=5):
    """Search memory entries for a user based on similarity."""
    try:
        # Get vector embedding for query
        query_embedding = simple_embedding(query)
        
        # Very basic similarity function
        def similarity(emb1, emb2):
            if len(emb1) != len(emb2):
                # Handle different lengths (should be same in our implementation)
                min_len = min(len(emb1), len(emb2))
                emb1 = emb1[:min_len]
                emb2 = emb2[:min_len]
            
            # Calculate dot product (very simple similarity)
            dot_product = sum(a * b for a, b in zip(emb1, emb2))
            # Normalize
            similarity_score = max(0.0, min(1.0, dot_product / len(emb1)))
            return similarity_score
        
        # Search memory store
        memory_items = []
        for key, memory_item in memory_store.items():
            if str(memory_item["user_id"]) == str(user.id):
                sim_score = similarity(query_embedding, memory_item["embedding"])
                memory_items.append((memory_item, sim_score))
        
        # Sort by similarity score
        memory_items.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        memory_items = memory_items[:limit]
        
        # Format results
        memory_results = []
        for memory_item, score in memory_items:
            memory_id = memory_item["memory_id"]
            memory_entry = MemoryEntry.query.get(int(memory_id))
            if memory_entry:
                memory_results.append({
                    "id": memory_entry.id,
                    "type": memory_entry.entry_type,
                    "title": memory_entry.title,
                    "content": memory_entry.content,
                    "created_at": memory_entry.created_at.isoformat(),
                    "relevance": score
                })
        
        return memory_results
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return []

def get_memory_by_type(user, entry_type, limit=10):
    """Get memory entries of a specific type for a user."""
    try:
        entries = MemoryEntry.query.filter_by(
            user_id=user.id,
            entry_type=entry_type
        ).order_by(MemoryEntry.updated_at.desc()).limit(limit).all()
        
        results = []
        for entry in entries:
            results.append({
                "id": entry.id,
                "type": entry.entry_type,
                "title": entry.title,
                "content": entry.content,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            })
        
        return results
    except Exception as e:
        logger.error(f"Error getting memory by type: {e}")
        return []

def update_memory(memory_id, title=None, content=None, metadata=None):
    """Update an existing memory entry."""
    try:
        memory_entry = MemoryEntry.query.get(memory_id)
        if not memory_entry:
            return None
        
        # Update fields if provided
        if title:
            memory_entry.title = title
        if content:
            memory_entry.content = content
        if metadata:
            # Merge new metadata with existing
            current_metadata = memory_entry.meta_data or {}
            current_metadata.update(metadata)
            memory_entry.meta_data = current_metadata
        
        memory_entry.updated_at = datetime.utcnow()
        
        # Update vector embedding
        text_to_embed = f"{memory_entry.title} {memory_entry.content}"
        embedding = simple_embedding(text_to_embed)
        memory_entry.vector_embedding = json.dumps(embedding)
        
        db.session.commit()
        
        # Update in memory store
        memory_key = f"memory_{memory_id}"
        if memory_key in memory_store:
            memory_store[memory_key].update({
                "title": memory_entry.title,
                "content": memory_entry.content,
                "embedding": embedding,
                "text": text_to_embed
            })
        else:
            memory_store[memory_key] = {
                "user_id": str(memory_entry.user_id),
                "memory_id": str(memory_entry.id),
                "entry_type": memory_entry.entry_type,
                "title": memory_entry.title,
                "content": memory_entry.content,
                "embedding": embedding,
                "text": text_to_embed
            }
        
        return memory_entry
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        db.session.rollback()
        return None

def delete_memory(memory_id):
    """Delete a memory entry."""
    try:
        memory_entry = MemoryEntry.query.get(memory_id)
        if not memory_entry:
            return False
        
        # Delete from memory store
        memory_key = f"memory_{memory_id}"
        if memory_key in memory_store:
            del memory_store[memory_key]
        
        # Delete from SQL database
        db.session.delete(memory_entry)
        db.session.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        db.session.rollback()
        return False

def extract_memories_from_conversation(user, conversation_id):
    """Extract potential memory entries from a conversation."""
    try:
        from app import db
        from models import Message
        
        # Get all messages from the conversation
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.timestamp).all()
        
        if not messages:
            return []
        
        # Concatenate all messages into a single text
        conversation_text = "\n".join([f"{'User' if msg.is_user else 'Assistant'}: {msg.content}" for msg in messages])
        
        # Use OpenManus framework to extract important information
        from manus_integration import extract_memories
        
        memory_entries = extract_memories(user, conversation_text)
        return memory_entries
    except Exception as e:
        logger.error(f"Error extracting memories from conversation: {e}")
        return []
