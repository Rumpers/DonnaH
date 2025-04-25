import os
import logging
import json
from datetime import datetime
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from app import db
from models import MemoryEntry, Message

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize vector database
chroma_client = None
embedding_function = None
vector_db = None

def initialize_memory_system():
    """Initialize the memory system with vector database."""
    global chroma_client, embedding_function, vector_db
    
    try:
        # Initialize simpler embedding function for local development
        # This uses a smaller model that loads faster
        embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        # Initialize ChromaDB (with in-memory instance for development)
        persist_directory = os.path.join(os.getcwd(), "vector_db")
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB
        chroma_client = chromadb.PersistentClient(persist_directory)
        
        # Create collection
        vector_db = Chroma(
            client=chroma_client,
            collection_name="manus_memory",
            embedding_function=embedding_function
        )
        
        logger.info("Memory system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing memory system: {e}")
        return False

def add_memory(user, entry_type, title, content, metadata=None):
    """Add a new memory entry to the database and vector store."""
    try:
        # Create new memory entry
        metadata = metadata or {}
        
        # Generate vector embedding
        text_to_embed = f"{title} {content}"
        embedding = embedding_function.embed_query(text_to_embed)
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
        
        # Add to vector database
        vector_db.add_texts(
            texts=[text_to_embed],
            metadatas=[{
                "user_id": str(user.id),
                "memory_id": str(memory_entry.id),
                "entry_type": entry_type,
                "title": title
            }],
            ids=[f"memory_{memory_entry.id}"]
        )
        
        return memory_entry
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        db.session.rollback()
        raise

def search_memory(user, query, limit=5):
    """Search memory entries for a user based on similarity."""
    try:
        # Get vector embedding for query
        query_embedding = embedding_function.embed_query(query)
        
        # Search vector database
        results = vector_db.similarity_search_with_relevance_scores(
            query=query,
            k=limit,
            filter={"user_id": str(user.id)}
        )
        
        # Format results
        memory_results = []
        for doc, score in results:
            memory_id = doc.metadata.get("memory_id")
            if memory_id:
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
        embedding = embedding_function.embed_query(text_to_embed)
        memory_entry.vector_embedding = json.dumps(embedding)
        
        db.session.commit()
        
        # Update in vector database
        vector_db.delete(ids=[f"memory_{memory_id}"])
        vector_db.add_texts(
            texts=[text_to_embed],
            metadatas=[{
                "user_id": str(memory_entry.user_id),
                "memory_id": str(memory_entry.id),
                "entry_type": memory_entry.entry_type,
                "title": memory_entry.title
            }],
            ids=[f"memory_{memory_entry.id}"]
        )
        
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
        
        # Delete from vector database
        vector_db.delete(ids=[f"memory_{memory_id}"])
        
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
