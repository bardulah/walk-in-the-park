"""Tests for RAG system"""
import pytest
import tempfile
import shutil
from pathlib import Path
from utils.rag import SimpleFinancialRAG, FinancialDocument


class TestFinancialDocument:
    """Test FinancialDocument class"""

    def test_document_creation(self):
        """Test document creation"""
        doc = FinancialDocument(
            content="Apple reported strong Q4 earnings",
            ticker="AAPL",
            doc_type="10-Q",
            metadata={'quarter': 'Q4'}
        )

        assert doc.content == "Apple reported strong Q4 earnings"
        assert doc.ticker == "AAPL"
        assert doc.doc_type == "10-Q"
        assert doc.metadata['quarter'] == 'Q4'
        assert doc.id is not None

    def test_document_to_dict(self):
        """Test document serialization"""
        doc = FinancialDocument(
            content="Test content",
            ticker="MSFT",
            doc_type="10-K"
        )

        doc_dict = doc.to_dict()

        assert doc_dict['content'] == "Test content"
        assert doc_dict['ticker'] == "MSFT"
        assert doc_dict['doc_type'] == "10-K"
        assert 'timestamp' in doc_dict

    def test_document_from_dict(self):
        """Test document deserialization"""
        doc_dict = {
            'content': "Test",
            'ticker': "GOOGL",
            'doc_type': "earnings_transcript",
            'metadata': {'year': 2024}
        }

        doc = FinancialDocument.from_dict(doc_dict)

        assert doc.content == "Test"
        assert doc.ticker == "GOOGL"
        assert doc.metadata['year'] == 2024


class TestSimpleFinancialRAG:
    """Test SimpleFinancialRAG functionality"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def rag(self, temp_storage):
        """Create RAG instance with temp storage"""
        return SimpleFinancialRAG(storage_path=temp_storage)

    def test_init(self, rag):
        """Test RAG initialization"""
        assert rag is not None
        assert len(rag.documents) == 0

    def test_index_document(self, rag):
        """Test document indexing"""
        doc = rag.index_document(
            ticker='AAPL',
            content='Apple Q4 earnings beat expectations',
            doc_type='10-Q'
        )

        assert doc is not None
        assert len(rag.documents) == 1
        assert rag.documents[0].ticker == 'AAPL'

    def test_index_financial_report(self, rag):
        """Test financial report indexing with chunking"""
        long_report = "Revenue increased. " * 100  # 100 sentences

        docs = rag.index_financial_report(
            ticker='MSFT',
            report_type='10-K',
            content=long_report,
            chunk_size=200,
            chunk_overlap=50
        )

        assert len(docs) > 1  # Should be chunked
        assert all(d.ticker == 'MSFT' for d in docs)
        assert all(d.doc_type == '10-K' for d in docs)

    def test_retrieve_by_query(self, rag):
        """Test retrieval by query"""
        # Index some documents
        rag.index_document(
            ticker='AAPL',
            content='Apple reported strong revenue growth in Q4 2024',
            doc_type='10-Q'
        )
        rag.index_document(
            ticker='AAPL',
            content='Apple stock price increased significantly',
            doc_type='news'
        )
        rag.index_document(
            ticker='MSFT',
            content='Microsoft Azure revenue doubled',
            doc_type='10-K'
        )

        # Retrieve documents related to "revenue"
        context = rag.retrieve(query='revenue growth', ticker='AAPL', k=2)

        assert 'revenue' in context.lower()
        assert 'AAPL' in context

    def test_retrieve_with_ticker_filter(self, rag):
        """Test retrieval with ticker filter"""
        rag.index_document(ticker='AAPL', content='Apple earnings', doc_type='10-Q')
        rag.index_document(ticker='MSFT', content='Microsoft earnings', doc_type='10-Q')

        context = rag.retrieve(query='earnings', ticker='AAPL')

        assert 'Apple' in context
        assert 'Microsoft' not in context

    def test_retrieve_with_doc_type_filter(self, rag):
        """Test retrieval with document type filter"""
        rag.index_document(ticker='AAPL', content='Apple 10-K report', doc_type='10-K')
        rag.index_document(ticker='AAPL', content='Apple news article', doc_type='news')

        context = rag.retrieve(query='Apple', doc_type='10-K')

        assert '10-K' in context
        assert 'news' not in context

    def test_retrieve_no_results(self, rag):
        """Test retrieval with no matching documents"""
        rag.index_document(ticker='AAPL', content='Apple earnings', doc_type='10-Q')

        context = rag.retrieve(query='Microsoft Azure', ticker='MSFT')

        assert context == ""

    def test_calculate_similarity(self, rag):
        """Test similarity calculation"""
        similarity = rag._calculate_similarity(
            query='revenue growth',
            text='The company reported strong revenue growth in Q4'
        )

        assert similarity > 0.5  # Should have good similarity

        low_similarity = rag._calculate_similarity(
            query='revenue growth',
            text='The weather is nice today'
        )

        assert low_similarity < similarity

    def test_chunk_text(self, rag):
        """Test text chunking"""
        text = "A" * 1000

        chunks = rag._chunk_text(text, chunk_size=200, chunk_overlap=50)

        assert len(chunks) > 1
        assert all(len(c) <= 200 for c in chunks)

    def test_get_documents(self, rag):
        """Test get_documents with filters"""
        rag.index_document(ticker='AAPL', content='Apple', doc_type='10-K')
        rag.index_document(ticker='AAPL', content='Apple', doc_type='10-Q')
        rag.index_document(ticker='MSFT', content='Microsoft', doc_type='10-K')

        # Get all AAPL documents
        aapl_docs = rag.get_documents(ticker='AAPL')
        assert len(aapl_docs) == 2

        # Get all 10-K documents
        ten_k_docs = rag.get_documents(doc_type='10-K')
        assert len(ten_k_docs) == 2

        # Get AAPL 10-K documents
        aapl_10k = rag.get_documents(ticker='AAPL', doc_type='10-K')
        assert len(aapl_10k) == 1

    def test_clear_documents(self, rag):
        """Test document clearing"""
        rag.index_document(ticker='AAPL', content='Apple', doc_type='10-K')
        rag.index_document(ticker='MSFT', content='Microsoft', doc_type='10-K')

        assert len(rag.documents) == 2

        # Clear all documents
        rag.clear_documents()
        assert len(rag.documents) == 0

    def test_clear_documents_with_filter(self, rag):
        """Test document clearing with filter"""
        rag.index_document(ticker='AAPL', content='Apple', doc_type='10-K')
        rag.index_document(ticker='MSFT', content='Microsoft', doc_type='10-K')

        # Clear only AAPL documents
        rag.clear_documents(ticker='AAPL')
        assert len(rag.documents) == 1
        assert rag.documents[0].ticker == 'MSFT'

    def test_get_stats(self, rag):
        """Test statistics"""
        rag.index_document(ticker='AAPL', content='Apple', doc_type='10-K')
        rag.index_document(ticker='AAPL', content='Apple', doc_type='10-Q')
        rag.index_document(ticker='MSFT', content='Microsoft', doc_type='10-K')

        stats = rag.get_stats()

        assert stats['total_documents'] == 3
        assert stats['unique_tickers'] == 2
        assert stats['unique_doc_types'] == 2
        assert 'AAPL' in stats['ticker_counts']
        assert stats['ticker_counts']['AAPL'] == 2

    def test_persistence(self, temp_storage):
        """Test index persistence"""
        # Create RAG and index documents
        rag1 = SimpleFinancialRAG(storage_path=temp_storage)
        rag1.index_document(ticker='AAPL', content='Apple', doc_type='10-K')
        rag1.index_document(ticker='MSFT', content='Microsoft', doc_type='10-K')

        # Create new RAG instance pointing to same storage
        rag2 = SimpleFinancialRAG(storage_path=temp_storage)

        # Should load existing index
        assert len(rag2.documents) == 2
        assert any(d.ticker == 'AAPL' for d in rag2.documents)
        assert any(d.ticker == 'MSFT' for d in rag2.documents)
