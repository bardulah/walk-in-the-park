"""
Retrieval-Augmented Generation (RAG) for Financial Data
Grounds LLM responses in factual data to prevent hallucinations
"""
import json
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from config.logging_config import get_logger


logger = get_logger("rag")


class FinancialDocument:
    """Represents a financial document or data chunk"""

    def __init__(
        self,
        content: str,
        ticker: str,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize financial document

        Args:
            content: Document text content
            ticker: Stock ticker symbol
            doc_type: Type of document (e.g., '10-K', '10-Q', 'earnings_transcript', 'news')
            metadata: Additional metadata
            timestamp: Document timestamp
        """
        self.content = content
        self.ticker = ticker
        self.doc_type = doc_type
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()

        # Generate ID
        self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique document ID"""
        import hashlib
        key = f"{self.ticker}:{self.doc_type}:{self.timestamp.isoformat()}:{self.content[:100]}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            'id': self.id,
            'content': self.content,
            'ticker': self.ticker,
            'doc_type': self.doc_type,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialDocument':
        """Create from dict"""
        return cls(
            content=data['content'],
            ticker=data['ticker'],
            doc_type=data['doc_type'],
            metadata=data.get('metadata', {}),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
        )


class SimpleFinancialRAG:
    """
    Simple RAG system for financial data

    This is a lightweight implementation that uses basic text similarity
    instead of vector embeddings to keep it simple and dependency-free.

    For production, consider upgrading to:
    - ChromaDB + OpenAI Embeddings
    - Pinecone + Sentence Transformers
    - FAISS + HuggingFace Embeddings

    Usage:
        rag = SimpleFinancialRAG()

        # Index documents
        rag.index_document(ticker='AAPL', content='...', doc_type='10-K')

        # Retrieve relevant context
        context = rag.retrieve(query='revenue growth', ticker='AAPL', k=5)

        # Use context in LLM prompt
        prompt = f"Based on the following data:\\n{context}\\n\\nAnalyze..."
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize RAG system

        Args:
            storage_path: Path to store indexed documents
        """
        self.storage_path = Path(storage_path) if storage_path else Path('./data/rag_index')
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.documents: List[FinancialDocument] = []
        self.logger = logger

        # Load existing index
        self._load_index()

        self.logger.info(f"RAG initialized | Documents: {len(self.documents)}")

    def index_document(
        self,
        ticker: str,
        content: str,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FinancialDocument:
        """
        Index a financial document

        Args:
            ticker: Stock ticker
            content: Document content
            doc_type: Document type
            metadata: Additional metadata

        Returns:
            FinancialDocument instance
        """
        doc = FinancialDocument(
            content=content,
            ticker=ticker,
            doc_type=doc_type,
            metadata=metadata
        )

        self.documents.append(doc)
        self.logger.debug(f"Indexed document: {ticker} ({doc_type})")

        # Persist index
        self._save_index()

        return doc

    def index_financial_report(
        self,
        ticker: str,
        report_type: str,
        content: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[FinancialDocument]:
        """
        Index financial report by chunking into smaller pieces

        Args:
            ticker: Stock ticker
            report_type: Type of report ('10-K', '10-Q', etc.)
            content: Full report content
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of indexed documents
        """
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)

        documents = []
        for i, chunk in enumerate(chunks):
            doc = self.index_document(
                ticker=ticker,
                content=chunk,
                doc_type=report_type,
                metadata={'chunk_id': i, 'total_chunks': len(chunks)}
            )
            documents.append(doc)

        self.logger.info(f"Indexed {len(chunks)} chunks for {ticker} {report_type}")

        return documents

    def retrieve(
        self,
        query: str,
        ticker: Optional[str] = None,
        doc_type: Optional[str] = None,
        k: int = 5,
        min_similarity: float = 0.1
    ) -> str:
        """
        Retrieve relevant context for query

        Args:
            query: Search query
            ticker: Optional ticker filter
            doc_type: Optional document type filter
            k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            Combined context string
        """
        self.logger.debug(
            f"Retrieving context: query='{query[:50]}...' ticker={ticker} k={k}"
        )

        # Filter documents
        filtered_docs = self.documents

        if ticker:
            filtered_docs = [d for d in filtered_docs if d.ticker == ticker]

        if doc_type:
            filtered_docs = [d for d in filtered_docs if d.doc_type == doc_type]

        if not filtered_docs:
            self.logger.warning(f"No documents found for ticker={ticker} doc_type={doc_type}")
            return ""

        # Calculate similarity scores
        scored_docs = []
        for doc in filtered_docs:
            similarity = self._calculate_similarity(query, doc.content)

            if similarity >= min_similarity:
                scored_docs.append((doc, similarity))

        # Sort by similarity
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Take top-k
        top_docs = scored_docs[:k]

        if not top_docs:
            self.logger.warning(f"No documents meet similarity threshold {min_similarity}")
            return ""

        # Format context
        context_parts = []
        for doc, similarity in top_docs:
            context_parts.append(
                f"--- {doc.ticker} {doc.doc_type} (relevance: {similarity:.2f}) ---\n"
                f"{doc.content}\n"
            )

        context = "\n".join(context_parts)

        self.logger.debug(f"Retrieved {len(top_docs)} relevant documents")

        return context

    def get_documents(
        self,
        ticker: Optional[str] = None,
        doc_type: Optional[str] = None
    ) -> List[FinancialDocument]:
        """
        Get documents with optional filters

        Args:
            ticker: Optional ticker filter
            doc_type: Optional document type filter

        Returns:
            List of matching documents
        """
        docs = self.documents

        if ticker:
            docs = [d for d in docs if d.ticker == ticker]

        if doc_type:
            docs = [d for d in docs if d.doc_type == doc_type]

        return docs

    def clear_documents(self, ticker: Optional[str] = None, doc_type: Optional[str] = None):
        """
        Clear documents

        Args:
            ticker: Optional ticker filter
            doc_type: Optional document type filter
        """
        if ticker is None and doc_type is None:
            # Clear all
            self.documents = []
            self.logger.info("Cleared all documents")
        else:
            # Filter and remove
            before_count = len(self.documents)

            self.documents = [
                d for d in self.documents
                if not ((ticker is None or d.ticker != ticker) and
                       (doc_type is None or d.doc_type != doc_type))
            ]

            removed = before_count - len(self.documents)
            self.logger.info(f"Removed {removed} documents")

        self._save_index()

    def _calculate_similarity(self, query: str, text: str) -> float:
        """
        Calculate simple keyword-based similarity

        This is a basic implementation. For production, use:
        - Cosine similarity with embeddings
        - BM25 scoring
        - Dense retrieval models
        """
        query_lower = query.lower()
        text_lower = text.lower()

        # Extract keywords from query (simple word tokenization)
        query_words = set(query_lower.split())

        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        query_words = query_words - stop_words

        if not query_words:
            return 0.0

        # Count keyword matches
        matches = sum(1 for word in query_words if word in text_lower)

        # Calculate similarity score
        similarity = matches / len(query_words)

        # Bonus for exact phrase match
        if query_lower in text_lower:
            similarity += 0.3

        return min(similarity, 1.0)  # Cap at 1.0

    def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Split text into overlapping chunks

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - chunk_overlap

            # Prevent infinite loop
            if start + chunk_overlap >= len(text):
                break

        return chunks

    def _save_index(self):
        """Save index to disk"""
        index_file = self.storage_path / 'index.pkl'

        try:
            with open(index_file, 'wb') as f:
                pickle.dump([doc.to_dict() for doc in self.documents], f)

            self.logger.debug(f"Index saved: {len(self.documents)} documents")

        except Exception as e:
            self.logger.error(f"Failed to save index: {e}")

    def _load_index(self):
        """Load index from disk"""
        index_file = self.storage_path / 'index.pkl'

        if not index_file.exists():
            self.logger.debug("No existing index found")
            return

        try:
            with open(index_file, 'rb') as f:
                doc_dicts = pickle.load(f)

            self.documents = [FinancialDocument.from_dict(d) for d in doc_dicts]

            self.logger.info(f"Index loaded: {len(self.documents)} documents")

        except Exception as e:
            self.logger.error(f"Failed to load index: {e}")
            self.documents = []

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        tickers = set(d.ticker for d in self.documents)
        doc_types = set(d.doc_type for d in self.documents)

        doc_type_counts = {}
        for doc_type in doc_types:
            doc_type_counts[doc_type] = sum(1 for d in self.documents if d.doc_type == doc_type)

        ticker_counts = {}
        for ticker in tickers:
            ticker_counts[ticker] = sum(1 for d in self.documents if d.ticker == ticker)

        return {
            'total_documents': len(self.documents),
            'unique_tickers': len(tickers),
            'unique_doc_types': len(doc_types),
            'doc_type_counts': doc_type_counts,
            'ticker_counts': ticker_counts,
            'storage_path': str(self.storage_path)
        }

    def __repr__(self):
        return f"SimpleFinancialRAG(documents={len(self.documents)})"
