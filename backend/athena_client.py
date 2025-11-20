"""
AWS Athena client for querying wildfire data
"""
import boto3
import time
import os
from logger import get_logger

logger = get_logger(__name__)


class AthenaClient:
    """Client for querying AWS Athena"""

    def __init__(self, database='caffine_analytics_db', workgroup='caffine-analytics-workgroup', region='eu-central-1'):
        """
        Initialize Athena client

        Args:
            database: Glue database name
            workgroup: Athena workgroup name
            region: AWS region
        """
        # Create a session with explicit credentials from environment
        session = boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=os.getenv('AWS_SESSION_TOKEN'),  # For temporary credentials
            region_name=region
        )
        
        self.client = session.client('athena')
        self.database = database
        self.workgroup = workgroup
        self.region = region
        
        # Log credential status (without exposing actual values)
        has_access_key = bool(os.getenv('AWS_ACCESS_KEY_ID'))
        has_secret_key = bool(os.getenv('AWS_SECRET_ACCESS_KEY'))
        has_session_token = bool(os.getenv('AWS_SESSION_TOKEN'))
        
        logger.info(
            f"Initialized Athena client for database: {database}, workgroup: {workgroup}, "
            f"region: {region}, credentials: access_key={has_access_key}, "
            f"secret_key={has_secret_key}, session_token={has_session_token}"
        )

    def execute_query(self, query, max_wait_seconds=60):
        """
        Execute Athena query and return results

        Args:
            query: SQL query string
            max_wait_seconds: Maximum time to wait for query completion

        Returns:
            List of dictionaries containing query results
        """
        logger.info(f"Executing Athena query: {query}")

        try:
            # Start query execution
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': self.database},
                WorkGroup=self.workgroup
            )

            query_execution_id = response['QueryExecutionId']
            logger.info(f"Query execution started with ID: {query_execution_id}")

            # Wait for query to complete
            status = self._wait_for_query_completion(query_execution_id, max_wait_seconds)

            if status != 'SUCCEEDED':
                logger.error(f"Query failed with status: {status}")
                raise Exception(f"Query failed with status: {status}")

            # Get query results
            results = self._get_query_results(query_execution_id)
            logger.info(f"Query returned {len(results)} rows")

            return results

        except Exception as e:
            logger.error(f"Error executing Athena query: {e}")
            raise

    def _wait_for_query_completion(self, query_execution_id, max_wait_seconds):
        """Wait for query to complete and return status"""
        start_time = time.time()

        while True:
            response = self.client.get_query_execution(QueryExecutionId=query_execution_id)
            status = response['QueryExecution']['Status']['State']

            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                # Log failure details if query failed
                if status == 'FAILED':
                    state_change_reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown reason')
                    logger.error(f"Query failed. Reason: {state_change_reason}")
                return status

            if time.time() - start_time > max_wait_seconds:
                logger.error(f"Query timeout after {max_wait_seconds} seconds")
                raise TimeoutError(f"Query execution timeout after {max_wait_seconds} seconds")

            time.sleep(1)

    def _get_query_results(self, query_execution_id):
        """Get query results and convert to list of dictionaries"""
        results = []
        next_token = None

        while True:
            params = {'QueryExecutionId': query_execution_id}
            if next_token:
                params['NextToken'] = next_token

            response = self.client.get_query_results(**params)

            # Get column names from first row
            if not results and response['ResultSet']['Rows']:
                column_info = response['ResultSet']['Rows'][0]['Data']
                column_names = [col.get('VarCharValue', '') for col in column_info]

                # Process data rows (skip header row)
                for row in response['ResultSet']['Rows'][1:]:
                    row_data = {}
                    for i, col in enumerate(row['Data']):
                        value = col.get('VarCharValue')
                        # Convert numeric strings to appropriate types
                        if value is not None:
                            try:
                                # Try to convert to float for numeric columns
                                if column_names[i] in ['latitude', 'longitude', 'frp', 'brightness', 'bright_t31', 'scan', 'track']:
                                    value = float(value)
                                elif column_names[i] in ['year']:
                                    value = int(value)
                            except (ValueError, TypeError):
                                pass  # Keep as string
                        row_data[column_names[i]] = value
                    results.append(row_data)
            else:
                # Process subsequent pages
                for row in response['ResultSet']['Rows']:
                    row_data = {}
                    for i, col in enumerate(row['Data']):
                        value = col.get('VarCharValue')
                        if value is not None:
                            try:
                                if column_names[i] in ['latitude', 'longitude', 'frp', 'brightness', 'bright_t31', 'scan', 'track']:
                                    value = float(value)
                                elif column_names[i] in ['year']:
                                    value = int(value)
                            except (ValueError, TypeError):
                                pass
                        row_data[column_names[i]] = value
                    results.append(row_data)

            # Check if there are more results
            next_token = response.get('NextToken')
            if not next_token:
                break

        return results

    def query_wildfire_by_bbox(self, min_lat, max_lat, min_lon, max_lon, limit=1000, start_date=None, end_date=None):
        """
        Query wildfire data by bounding box and optional date range

        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            limit: Maximum number of results to return
            start_date: Start date (YYYY-MM-DD format, optional)
            end_date: End date (YYYY-MM-DD format, optional)

        Returns:
            List of wildfire records
        """
        # Build WHERE clause with spatial bounds
        # Cast latitude/longitude to DOUBLE for proper numeric comparison
        where_clauses = [
            f"CAST(latitude AS DOUBLE) BETWEEN {min_lat} AND {max_lat}",
            f"CAST(longitude AS DOUBLE) BETWEEN {min_lon} AND {max_lon}"
        ]
        
        # Add date filters if provided using year/month columns
        # Try treating year and month as integers
        if start_date and end_date:
            # Parse dates to extract year, month as integers
            start_parts = start_date.split('-')
            start_year = int(start_parts[0])
            start_month = int(start_parts[1])
            
            end_parts = end_date.split('-')
            end_year = int(end_parts[0])
            end_month = int(end_parts[1])
            
            # For same year and month, just filter by that month
            if start_year == end_year and start_month == end_month:
                where_clauses.append(f"(CAST(year AS INTEGER) = {start_year} AND CAST(month AS INTEGER) = {start_month})")
            else:
                # For different months/years
                where_clauses.append(f"CAST(year AS INTEGER) = {start_year} AND CAST(month AS INTEGER) = {start_month}")
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
        SELECT 
            latitude, longitude, acq_date, acq_time, 
            confidence, frp, brightness, bright_t31,
            instrument, satellite, version, daynight, 
            type, scan, track, year, month, day
        FROM wild_fire
        WHERE {where_clause}
        LIMIT {limit}
        """

        return self.execute_query(query)


# Singleton instance
_athena_client = None


def get_athena_client():
    """Get or create Athena client singleton"""
    global _athena_client
    if _athena_client is None:
        _athena_client = AthenaClient()
    return _athena_client
