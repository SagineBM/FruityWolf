"""
Database Package

SQLite database access layer with migrations support.
"""

from .models import (
    Database,
    get_db,
    get_app_data_path,
    get_cache_path,
    get_db_path,
    execute,
    execute_many,
    batch_transaction,
    query,
    query_one,
    get_setting,
    set_setting,
)

from .migrations import (
    Migration,
    MigrationRunner,
    run_migrations,
    MIGRATIONS,
)

__all__ = [
    # Database
    'Database',
    'get_db',
    
    # Paths
    'get_app_data_path',
    'get_cache_path',
    'get_db_path',
    
    # Query functions
    'execute',
    'execute_many',
    'batch_transaction',
    'query',
    'query_one',
    
    # Settings
    'get_setting',
    'set_setting',
    
    # Migrations
    'Migration',
    'MigrationRunner',
    'run_migrations',
    'MIGRATIONS',
]

