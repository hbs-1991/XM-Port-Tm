"""
Integration tests for XML Storage Service S3 functionality
"""
import pytest
import io
import boto3
from unittest.mock import AsyncMock, patch, MagicMock
from moto import mock_s3
from sqlalchemy.orm import Session

from src.services.xml_storage import XMLStorageService
from src.models.user import User, SubscriptionTier
from src.models.processing_job import ProcessingJob, ProcessingStatus
from src.models.product_match import ProductMatch


@pytest.fixture
def test_user():
    """Create test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.BASIC,
        credits_remaining=100,
        credits_used_this_month=0
    )


@pytest.fixture
def test_job(db_session: Session, test_user: User):
    """Create test processing job"""
    db_session.add(test_user)
    db_session.commit()
    
    job = ProcessingJob(
        user_id=test_user.id,
        filename="test_products.csv",
        original_filename="test_products.csv",
        file_size=1024,
        file_url="s3://test-bucket/uploads/1/test_products.csv",
        status=ProcessingStatus.PROCESSING,
        total_products=3,
        country_schema="turkmenistan"
    )
    db_session.add(job)
    db_session.commit()
    return job


@pytest.fixture
def test_product_matches(db_session: Session, test_job: ProcessingJob):
    """Create test product matches"""
    matches = [
        ProductMatch(
            job_id=test_job.id,
            product_description="Apple iPhone 14",
            matched_hs_code="8517.12.00",
            confidence_score=0.95,
            quantity=10,
            unit_of_measure="pcs",
            value=12000.00,
            origin_country="China",
            unit_price=1200.00,
            requires_manual_review=False,
            vector_store_reasoning="iPhone is clearly a cellular telephone"
        ),
        ProductMatch(
            job_id=test_job.id,
            product_description="Samsung Galaxy S23",
            matched_hs_code="8517.12.00",
            confidence_score=0.92,
            quantity=5,
            unit_of_measure="pcs",
            value=4000.00,
            origin_country="South Korea",
            unit_price=800.00,
            requires_manual_review=False,
            vector_store_reasoning="Samsung Galaxy is a cellular telephone"
        ),
        ProductMatch(
            job_id=test_job.id,
            product_description="Dell Laptop XPS 13",
            matched_hs_code="8471.30.01",
            confidence_score=0.88,
            quantity=3,
            unit_of_measure="pcs",
            value=3600.00,
            origin_country="Taiwan",
            unit_price=1200.00,
            requires_manual_review=True,
            vector_store_reasoning="Dell XPS 13 is a portable laptop computer"
        )
    ]
    
    for match in matches:
        db_session.add(match)
    db_session.commit()
    
    return matches


@pytest.fixture
def sample_xml_content():
    """Create sample XML content for testing"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<ns0:Declaration xmlns:ns0="http://www.asycuda.org/asycuda">
    <ns0:Header>
        <ns0:Country_code>TM</ns0:Country_code>
        <ns0:Declaration_number>TEST001</ns0:Declaration_number>
        <ns0:Date>2025-01-23</ns0:Date>
    </ns0:Header>
    <ns0:Items>
        <ns0:Item>
            <ns0:Description>Apple iPhone 14</ns0:Description>
            <ns0:HS_code>8517.12.00</ns0:HS_code>
            <ns0:Quantity>10</ns0:Quantity>
            <ns0:Value>12000.00</ns0:Value>
        </ns0:Item>
        <ns0:Item>
            <ns0:Description>Samsung Galaxy S23</ns0:Description>
            <ns0:HS_code>8517.12.00</ns0:HS_code>
            <ns0:Quantity>5</ns0:Quantity>
            <ns0:Value>4000.00</ns0:Value>
        </ns0:Item>
    </ns0:Items>
</ns0:Declaration>"""


class TestXMLStorageS3Integration:
    """Integration tests for XML Storage Service S3 functionality"""

    @mock_s3
    @pytest.mark.asyncio
    async def test_s3_xml_storage_success(
        self,
        db_session: Session,
        test_job: ProcessingJob,
        test_product_matches: list,
        sample_xml_content: str
    ):
        """Test successful XML file storage to S3"""
        
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-xml-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock the S3 configuration
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.return_value = {
                'bucket_name': bucket_name,
                's3_client': s3_client,
                'region': 'us-east-1'
            }
            
            # Store XML file
            result = await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=sample_xml_content,
                country_schema='turkmenistan',
                product_matches=test_product_matches
            )
            
            # Verify successful storage
            assert result is not None
            assert 'file_path' in result
            assert 'download_url' in result
            assert 'file_size' in result
            assert 'expires_at' in result
            
            # Verify S3 file was created
            s3_key = result['file_path'].split('/')[-1]
            response = s3_client.get_object(Bucket=bucket_name, Key=f"xml/{s3_key}")
            stored_content = response['Body'].read().decode('utf-8')
            assert sample_xml_content in stored_content
            
            # Verify file size matches
            assert result['file_size'] == len(sample_xml_content.encode('utf-8'))

    @mock_s3
    @pytest.mark.asyncio
    async def test_s3_presigned_url_generation(
        self,
        db_session: Session,
        test_job: ProcessingJob,
        test_product_matches: list,
        sample_xml_content: str
    ):
        """Test pre-signed URL generation for XML downloads"""
        
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-xml-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock the S3 configuration
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.return_value = {
                'bucket_name': bucket_name,
                's3_client': s3_client,
                'region': 'us-east-1'
            }
            
            # Store XML file
            result = await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=sample_xml_content,
                country_schema='turkmenistan',
                product_matches=test_product_matches
            )
            
            # Verify pre-signed URL was generated
            assert result['download_url'].startswith('https://')
            assert bucket_name in result['download_url']
            assert 'Signature' in result['download_url']
            assert 'Expires' in result['download_url']
            
            # Verify expiration is set (default 1 hour)
            assert result['expires_at'] is not None

    @pytest.mark.asyncio
    async def test_s3_connection_failure_fallback(
        self,
        db_session: Session,
        test_job: ProcessingJob,
        test_product_matches: list,
        sample_xml_content: str
    ):
        """Test fallback to local storage when S3 is unavailable"""
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock S3 to fail
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.side_effect = Exception("S3 connection failed")
            
            # Mock local storage
            with patch.object(storage_service, '_store_locally', new_callable=AsyncMock) as mock_local:
                mock_local.return_value = {
                    'file_path': '/tmp/xml/job_1_export.xml',
                    'download_url': 'http://localhost:8000/api/v1/processing/1/xml-download',
                    'file_size': len(sample_xml_content.encode('utf-8')),
                    'expires_at': '2025-01-23T12:00:00Z'
                }
                
                # Store XML file
                result = await storage_service.store_xml_file(
                    job_id=test_job.id,
                    xml_content=sample_xml_content,
                    country_schema='turkmenistan',
                    product_matches=test_product_matches
                )
                
                # Verify fallback to local storage
                assert result is not None
                assert result['file_path'].startswith('/tmp/')
                assert 'localhost' in result['download_url']
                mock_local.assert_called_once()

    @mock_s3
    @pytest.mark.asyncio
    async def test_s3_large_file_handling(
        self,
        db_session: Session,
        test_job: ProcessingJob
    ):
        """Test S3 storage with large XML files"""
        
        # Create large product matches list
        large_matches = []
        for i in range(1000):  # 1000 products
            match = ProductMatch(
                job_id=test_job.id,
                product_description=f"Product {i}",
                matched_hs_code="9999.99.99",
                confidence_score=0.9,
                quantity=i + 1,
                unit_of_measure="pcs",
                value=float((i + 1) * 100),
                origin_country="China",
                unit_price=100.0,
                requires_manual_review=False,
                vector_store_reasoning=f"Test reasoning for product {i}"
            )
            large_matches.append(match)
            db_session.add(match)
        
        db_session.commit()
        
        # Create large XML content (simulate large file)
        large_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        large_xml += '<ns0:Declaration xmlns:ns0="http://www.asycuda.org/asycuda">\n'
        large_xml += '    <ns0:Header>\n'
        large_xml += '        <ns0:Country_code>TM</ns0:Country_code>\n'
        large_xml += '    </ns0:Header>\n'
        large_xml += '    <ns0:Items>\n'
        
        for i in range(1000):
            large_xml += f'        <ns0:Item>\n'
            large_xml += f'            <ns0:Description>Product {i}</ns0:Description>\n'
            large_xml += f'            <ns0:HS_code>9999.99.99</ns0:HS_code>\n'
            large_xml += f'            <ns0:Quantity>{i + 1}</ns0:Quantity>\n'
            large_xml += f'            <ns0:Value>{(i + 1) * 100.0}</ns0:Value>\n'
            large_xml += f'        </ns0:Item>\n'
        
        large_xml += '    </ns0:Items>\n'
        large_xml += '</ns0:Declaration>'
        
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-xml-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock the S3 configuration
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.return_value = {
                'bucket_name': bucket_name,
                's3_client': s3_client,
                'region': 'us-east-1'
            }
            
            # Store large XML file
            result = await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=large_xml,
                country_schema='turkmenistan',
                product_matches=large_matches
            )
            
            # Verify successful storage of large file
            assert result is not None
            assert result['file_size'] > 50000  # Should be > 50KB
            
            # Verify S3 file was created and content is correct
            s3_key = result['file_path'].split('/')[-1]
            response = s3_client.get_object(Bucket=bucket_name, Key=f"xml/{s3_key}")
            stored_content = response['Body'].read().decode('utf-8')
            assert len(stored_content) == len(large_xml)
            assert "Product 999" in stored_content  # Verify last product was included

    @mock_s3
    @pytest.mark.asyncio
    async def test_s3_file_metadata_and_tagging(
        self,
        db_session: Session,
        test_job: ProcessingJob,
        test_product_matches: list,
        sample_xml_content: str
    ):
        """Test S3 file metadata and tagging"""
        
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-xml-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock the S3 configuration
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.return_value = {
                'bucket_name': bucket_name,
                's3_client': s3_client,
                'region': 'us-east-1'
            }
            
            # Store XML file
            result = await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=sample_xml_content,
                country_schema='turkmenistan',
                product_matches=test_product_matches
            )
            
            # Verify file was stored
            assert result is not None
            
            # Get S3 object metadata
            s3_key = result['file_path'].split('/')[-1]
            response = s3_client.head_object(Bucket=bucket_name, Key=f"xml/{s3_key}")
            
            # Verify content type and encoding
            assert response['ContentType'] == 'application/xml'
            assert response['ContentEncoding'] == 'utf-8'
            
            # Verify metadata was set
            metadata = response.get('Metadata', {})
            assert 'job-id' in metadata
            assert 'country-schema' in metadata
            assert metadata['job-id'] == str(test_job.id)
            assert metadata['country-schema'] == 'turkmenistan'

    @pytest.mark.asyncio
    async def test_s3_file_validation_and_size_limits(
        self,
        db_session: Session,
        test_job: ProcessingJob,
        test_product_matches: list
    ):
        """Test file validation and size limits"""
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Test with oversized content (simulate > 50MB limit)
        oversized_content = "x" * (50 * 1024 * 1024 + 1)  # 50MB + 1 byte
        
        # Should reject oversized file
        with pytest.raises(Exception) as exc_info:
            await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=oversized_content,
                country_schema='turkmenistan',
                product_matches=test_product_matches
            )
        assert "File size exceeds maximum limit" in str(exc_info.value)
        
        # Test with invalid XML content
        invalid_xml = "This is not XML content"
        
        with pytest.raises(Exception) as exc_info:
            await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=invalid_xml,
                country_schema='turkmenistan',
                product_matches=test_product_matches
            )
        assert "Invalid XML content" in str(exc_info.value)

    @mock_s3
    @pytest.mark.asyncio
    async def test_s3_concurrent_uploads(
        self,
        db_session: Session,
        test_user: User,
        sample_xml_content: str
    ):
        """Test concurrent XML uploads to S3"""
        
        # Create multiple processing jobs
        jobs = []
        for i in range(5):
            job = ProcessingJob(
                user_id=test_user.id,
                filename=f"test_products_{i}.csv",
                original_filename=f"test_products_{i}.csv",
                file_size=1024,
                file_url=f"s3://test-bucket/uploads/1/test_products_{i}.csv",
                status=ProcessingStatus.PROCESSING,
                total_products=3,
                country_schema="turkmenistan"
            )
            db_session.add(job)
            jobs.append(job)
        
        db_session.commit()
        
        # Create product matches for each job
        all_matches = []
        for i, job in enumerate(jobs):
            match = ProductMatch(
                job_id=job.id,
                product_description=f"Product {i}",
                matched_hs_code="8517.12.00",
                confidence_score=0.95,
                quantity=10,
                unit_of_measure="pcs",
                value=1000.00,
                origin_country="China",
                unit_price=100.00,
                requires_manual_review=False,
                vector_store_reasoning="Test reasoning"
            )
            db_session.add(match)
            all_matches.append([match])
        
        db_session.commit()
        
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-xml-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock the S3 configuration
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.return_value = {
                'bucket_name': bucket_name,
                's3_client': s3_client,
                'region': 'us-east-1'
            }
            
            # Create concurrent upload tasks
            tasks = []
            for i, (job, matches) in enumerate(zip(jobs, all_matches)):
                task = storage_service.store_xml_file(
                    job_id=job.id,
                    xml_content=sample_xml_content.replace("TEST001", f"TEST00{i+1}"),
                    country_schema='turkmenistan',
                    product_matches=matches
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            import asyncio
            results = await asyncio.gather(*tasks)
            
            # Verify all uploads succeeded
            assert len(results) == 5
            for i, result in enumerate(results):
                assert result is not None
                assert 'file_path' in result
                assert 'download_url' in result
                
                # Verify unique file paths
                for j, other_result in enumerate(results):
                    if i != j:
                        assert result['file_path'] != other_result['file_path']
            
            # Verify all files exist in S3
            s3_objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix='xml/')
            assert s3_objects['KeyCount'] == 5

    @pytest.mark.asyncio
    async def test_s3_error_handling_and_retry(
        self,
        db_session: Session,
        test_job: ProcessingJob,
        test_product_matches: list,
        sample_xml_content: str
    ):
        """Test S3 error handling and retry logic"""
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock S3 client to fail initially then succeed
        call_count = 0
        
        def mock_upload_fileobj(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 attempts
                raise Exception("S3 service temporarily unavailable")
            return None  # Success on 3rd attempt
        
        mock_s3_client = MagicMock()
        mock_s3_client.upload_fileobj.side_effect = mock_upload_fileobj
        mock_s3_client.generate_presigned_url.return_value = 'https://presigned-url.com'
        mock_s3_client.head_object.return_value = {'ContentLength': len(sample_xml_content)}
        
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.return_value = {
                'bucket_name': 'test-bucket',
                's3_client': mock_s3_client,
                'region': 'us-east-1'
            }
            
            # Store XML file - should succeed after retries
            result = await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=sample_xml_content,
                country_schema='turkmenistan',
                product_matches=test_product_matches
            )
            
            # Verify success after retries
            assert result is not None
            assert call_count == 3  # Should have retried twice
            assert mock_s3_client.upload_fileobj.call_count == 3

    @pytest.mark.asyncio
    async def test_s3_cleanup_and_retention(
        self,
        db_session: Session,
        test_job: ProcessingJob,
        test_product_matches: list,
        sample_xml_content: str
    ):
        """Test S3 file cleanup and retention policies"""
        
        # Initialize storage service
        storage_service = XMLStorageService()
        
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_s3_client.upload_fileobj.return_value = None
        mock_s3_client.generate_presigned_url.return_value = 'https://presigned-url.com'
        mock_s3_client.head_object.return_value = {'ContentLength': len(sample_xml_content)}
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'xml/old_file.xml',
                    'LastModified': '2024-12-01T00:00:00Z',
                    'Size': 1024
                }
            ]
        }
        mock_s3_client.delete_object.return_value = None
        
        with patch.object(storage_service, '_get_s3_config') as mock_config:
            mock_config.return_value = {
                'bucket_name': 'test-bucket',
                's3_client': mock_s3_client,
                'region': 'us-east-1'
            }
            
            # Store XML file with cleanup enabled
            result = await storage_service.store_xml_file(
                job_id=test_job.id,
                xml_content=sample_xml_content,
                country_schema='turkmenistan',
                product_matches=test_product_matches,
                cleanup_old_files=True
            )
            
            # Verify file was stored
            assert result is not None
            
            # Verify cleanup was attempted
            mock_s3_client.list_objects_v2.assert_called_once()
            mock_s3_client.delete_object.assert_called_once()