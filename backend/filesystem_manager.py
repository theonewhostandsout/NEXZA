import os
import logging
import hashlib
import shutil
import tempfile
import mimetypes
from typing import Union, Tuple, List, Dict, Optional, Any
from threading import RLock
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
from functools import lru_cache
from collections import defaultdict
import time

class FileSystemManager:
    """
    Enhanced secure file system manager with advanced caching, monitoring, and security features.
    Provides sandboxed file operations with comprehensive audit logging and performance optimization.
    """

    def __init__(self, base_dir: str, max_cache_size: int = 100, enable_versioning: bool = True):
        """
        Initialize FileSystemManager with enhanced security and performance features.
        
        Args:
            base_dir: Base directory for all file operations
            max_cache_size: Maximum number of files to cache in memory
            enable_versioning: Enable automatic file versioning for modifications
        """
        self.base_dir = os.path.abspath(base_dir)
        self._lock = RLock()
        self._file_cache = {}  # LRU cache for frequently accessed files
        self._cache_access_times = {}
        self._max_cache_size = max_cache_size
        self._enable_versioning = enable_versioning
        
        # Performance metrics
        self._operation_metrics = defaultdict(lambda: {'count': 0, 'total_time': 0, 'errors': 0})
        self._last_cleanup = datetime.now()
        
        # Security: Track file access patterns for anomaly detection
        self._access_log = defaultdict(list)
        self._suspicious_patterns = []
        
        # Initialize directory structure
        self._initialize_directories()
        
        # Setup enhanced logging
        self._setup_logging()
        
        # File integrity tracking
        self._file_checksums = {}
        self._load_checksums()
        
        self.logger.info(f"Enhanced FileSystemManager initialized: base={self.base_dir}, cache={max_cache_size}, versioning={enable_versioning}")

    def _initialize_directories(self):
        """Create required directory structure with proper permissions."""
        required_dirs = [
            '',  # Base directory
            'logs',
            'temp',
            'archive',
            'versions',
            'metadata',
            'memory_shortterm',
            'code',
            'documentation',
            'data',
            'configuration',
            'business',
            'unsorted'
        ]
        
        for dir_path in required_dirs:
            full_path = os.path.join(self.base_dir, dir_path)
            try:
                os.makedirs(full_path, exist_ok=True)
                # Set directory permissions (Unix-like systems)
                if hasattr(os, 'chmod'):
                    os.chmod(full_path, 0o755)
            except Exception as e:
                # Continue even if some directories fail
                print(f"Warning: Could not create directory {full_path}: {e}")

    def _setup_logging(self):
        """Configure enhanced logging with rotation and compression."""
        log_dir = os.path.join(self.base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Create logger with unique name
        self.logger = logging.getLogger(f'FileSystemManager_{id(self)}')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation
        log_file = os.path.join(log_dir, f'filesystem_{datetime.now().strftime("%Y%m%d")}.log')
        
        try:
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
        except ImportError:
            # Fallback to basic FileHandler
            handler = logging.FileHandler(log_file, encoding='utf-8')
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _is_path_safe(self, path: str) -> bool:
        """
        Enhanced path validation with multiple security checks.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Convert to absolute path
            requested_path = os.path.abspath(os.path.join(self.base_dir, path))
            
            # Check if path is within base directory
            if not requested_path.startswith(self.base_dir):
                self._log_security_event(f"Path traversal attempt: {path}")
                return False
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r'\.\./\.\./\.\.',  # Multiple traversals
                r'\.\.\\\.\.\\\.\.', # Windows traversals
                r'/etc/',  # System directories
                r'C:\\Windows',  # Windows system
                r'/proc/',  # Process information
                r'\.git/',  # Version control
                r'\.env',  # Environment files
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    self._log_security_event(f"Suspicious pattern detected: {path}")
                    return False
            
            # Additional checks for file names
            filename = os.path.basename(path)
            if filename.startswith('.') and filename not in ['.gitignore', '.env.example']:
                self._log_security_event(f"Hidden file access attempt: {path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Path validation error: {e}")
            return False

    def _log_security_event(self, message: str):
        """Log security-related events for audit and monitoring."""
        timestamp = datetime.now().isoformat()
        security_log = os.path.join(self.base_dir, 'logs', 'security.log')
        
        with self._lock:
            try:
                with open(security_log, 'a', encoding='utf-8') as f:
                    f.write(f"{timestamp} - SECURITY - {message}\n")
                self.logger.warning(f"Security event: {message}")
            except Exception as e:
                self.logger.error(f"Failed to log security event: {e}")

    def _track_operation(self, operation: str, duration: float, success: bool):
        """Track operation metrics for performance monitoring."""
        with self._lock:
            metrics = self._operation_metrics[operation]
            metrics['count'] += 1
            metrics['total_time'] += duration
            if not success:
                metrics['errors'] += 1

    def _check_cache(self, filepath: str) -> Optional[Any]:
        """Check if file content is cached and still valid."""
        if filepath in self._file_cache:
            cache_time = self._cache_access_times.get(filepath)
            if cache_time and (datetime.now() - cache_time) < timedelta(minutes=5):
                self._cache_access_times[filepath] = datetime.now()
                return self._file_cache[filepath]
            else:
                # Cache expired
                del self._file_cache[filepath]
                del self._cache_access_times[filepath]
        return None

    def _update_cache(self, filepath: str, content: Any):
        """Update file cache with LRU eviction."""
        with self._lock:
            # Remove oldest entry if cache is full
            if len(self._file_cache) >= self._max_cache_size:
                oldest = min(self._cache_access_times.items(), key=lambda x: x[1])
                del self._file_cache[oldest[0]]
                del self._cache_access_times[oldest[0]]
            
            self._file_cache[filepath] = content
            self._cache_access_times[filepath] = datetime.now()

    def _calculate_checksum(self, content: Union[str, bytes]) -> str:
        """Calculate SHA-256 checksum for content."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def _verify_integrity(self, filepath: str, content: Union[str, bytes]) -> bool:
        """Verify file integrity using checksums."""
        calculated_checksum = self._calculate_checksum(content)
        stored_checksum = self._file_checksums.get(filepath)
        
        if stored_checksum and stored_checksum != calculated_checksum:
            self._log_security_event(f"Integrity check failed for {filepath}")
            return False
        
        # Update checksum
        self._file_checksums[filepath] = calculated_checksum
        return True

    def _save_checksums(self):
        """Persist checksums to disk."""
        try:
            checksum_file = os.path.join(self.base_dir, 'metadata', 'checksums.json')
            with self._lock:
                with open(checksum_file, 'w', encoding='utf-8') as f:
                    json.dump(self._file_checksums, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save checksums: {e}")

    def _load_checksums(self):
        """Load checksums from disk."""
        try:
            checksum_file = os.path.join(self.base_dir, 'metadata', 'checksums.json')
            if os.path.exists(checksum_file):
                with open(checksum_file, 'r', encoding='utf-8') as f:
                    self._file_checksums = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load checksums: {e}")
            self._file_checksums = {}

    def _create_version(self, filepath: str):
        """Create a versioned backup of a file before modification."""
        if not self._enable_versioning:
            return
        
        try:
            if os.path.exists(filepath):
                version_dir = os.path.join(self.base_dir, 'versions')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                relative_path = os.path.relpath(filepath, self.base_dir)
                version_name = f"{relative_path.replace(os.sep, '_')}_{timestamp}"
                version_path = os.path.join(version_dir, version_name)
                
                shutil.copy2(filepath, version_path)
                self.logger.info(f"Created version: {version_name}")
        except Exception as e:
            self.logger.error(f"Failed to create version: {e}")

    def read_file(self, filename: str, use_cache: bool = True) -> Tuple[bool, Union[str, None]]:
        """
        Read a text file with caching and integrity verification.
        
        Args:
            filename: Name of file to read
            use_cache: Whether to use caching
            
        Returns:
            Tuple of (success, content or error message)
        """
        start_time = time.time()
        success = False
        
        try:
            # Validate path
            if not self._is_path_safe(filename):
                return False, "Access denied: Invalid path"
            
            file_path = os.path.normpath(os.path.join(self.base_dir, filename))
            
            # Check cache first
            if use_cache:
                cached_content = self._check_cache(file_path)
                if cached_content is not None:
                    self.logger.debug(f"Cache hit for {filename}")
                    return True, cached_content
            
            # Check file existence
            if not os.path.exists(file_path):
                return False, f"File not found: {filename}"
            
            if not os.path.isfile(file_path):
                return False, f"Not a file: {filename}"
            
            # Read file with lock
            with self._lock:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            # Verify integrity
            if not self._verify_integrity(file_path, content):
                self.logger.warning(f"Integrity check failed for {filename}")
            
            # Update cache
            if use_cache:
                self._update_cache(file_path, content)
            
            # Log access
            self._access_log[filename].append(datetime.now())
            self.logger.info(f"File read: {filename} ({len(content)} bytes)")
            
            success = True
            return True, content
            
        except PermissionError:
            error_msg = f"Permission denied: {filename}"
            self.logger.error(error_msg)
            return False, error_msg
        except UnicodeDecodeError:
            error_msg = f"Unable to decode file: {filename}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        finally:
            duration = time.time() - start_time
            self._track_operation('read', duration, success)

    def write_file(self, filename: str, content: str, append: bool = False, 
                   create_backup: bool = True) -> Tuple[bool, str]:
        """
        Write or append to a file with versioning and integrity tracking.
        
        Args:
            filename: Name of file to write
            content: Content to write
            append: Whether to append instead of overwrite
            create_backup: Whether to create a backup version
            
        Returns:
            Tuple of (success, message)
        """
        start_time = time.time()
        success = False
        temp_file = None
        
        try:
            # Validate path
            if not self._is_path_safe(filename):
                return False, "Access denied: Invalid path"
            
            file_path = os.path.normpath(os.path.join(self.base_dir, filename))
            
            # Create backup/version if needed
            if create_backup and os.path.exists(file_path):
                self._create_version(file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to temporary file first (atomic write)
            with self._lock:
                temp_fd, temp_file = tempfile.mkstemp(dir=os.path.dirname(file_path))
                
                try:
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                        if append and os.path.exists(file_path):
                            # Read existing content for append
                            with open(file_path, 'r', encoding='utf-8') as existing:
                                f.write(existing.read())
                        f.write(content)
                    
                    # Atomic rename
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    os.rename(temp_file, file_path)
                    temp_file = None  # Prevent cleanup
                    
                except Exception as e:
                    raise e
                finally:
                    # Clean up temp file if needed
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
            
            # Update checksum
            self._file_checksums[file_path] = self._calculate_checksum(content)
            
            # Invalidate cache
            if file_path in self._file_cache:
                del self._file_cache[file_path]
                del self._cache_access_times[file_path]
            
            # Log operation
            action = "appended to" if append else "written"
            self.logger.info(f"File {action}: {filename} ({len(content)} bytes)")
            
            # Periodic checksum save
            if len(self._file_checksums) % 10 == 0:
                self._save_checksums()
            
            success = True
            return True, f"File {action} successfully: {filename}"
            
        except PermissionError:
            error_msg = f"Permission denied: {filename}"
            self.logger.error(error_msg)
            return False, error_msg
        except OSError as e:
            error_msg = f"OS error writing file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error writing file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        finally:
            duration = time.time() - start_time
            self._track_operation('write', duration, success)

    def write_binary_file(self, filename: str, content: bytes, 
                         create_backup: bool = True) -> Tuple[bool, str]:
        """
        Write binary data to a file with integrity tracking.
        
        Args:
            filename: Name of file to write
            content: Binary content to write
            create_backup: Whether to create a backup version
            
        Returns:
            Tuple of (success, message)
        """
        start_time = time.time()
        success = False
        
        try:
            # Validate path
            if not self._is_path_safe(filename):
                return False, "Access denied: Invalid path"
            
            file_path = os.path.normpath(os.path.join(self.base_dir, filename))
            
            # Validate content size (100MB limit for binary files)
            max_size = 100 * 1024 * 1024
            if len(content) > max_size:
                return False, f"Binary file too large: {len(content)} bytes (max {max_size})"
            
            # Create backup if needed
            if create_backup and os.path.exists(file_path):
                self._create_version(file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write binary data
            with self._lock:
                with open(file_path, 'wb') as f:
                    f.write(content)
            
            # Update checksum
            self._file_checksums[file_path] = self._calculate_checksum(content)
            
            self.logger.info(f"Binary file written: {filename} ({len(content)} bytes)")
            
            success = True
            return True, f"Binary file written: {filename}"
            
        except Exception as e:
            error_msg = f"Error writing binary file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        finally:
            duration = time.time() - start_time
            self._track_operation('write_binary', duration, success)

    def read_binary_file(self, filename: str) -> Tuple[bool, Union[bytes, str]]:
        """
        Read binary data from a file.
        
        Args:
            filename: Name of file to read
            
        Returns:
            Tuple of (success, content or error message)
        """
        start_time = time.time()
        success = False
        
        try:
            # Validate path
            if not self._is_path_safe(filename):
                return False, "Access denied: Invalid path"
            
            file_path = os.path.normpath(os.path.join(self.base_dir, filename))
            
            if not os.path.exists(file_path):
                return False, f"File not found: {filename}"
            
            # Read binary data
            with self._lock:
                with open(file_path, 'rb') as f:
                    content = f.read()
            
            self.logger.info(f"Binary file read: {filename} ({len(content)} bytes)")
            
            success = True
            return True, content
            
        except Exception as e:
            error_msg = f"Error reading binary file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        finally:
            duration = time.time() - start_time
            self._track_operation('read_binary', duration, success)

    def list_files(self, directory: str = "", include_dirs: bool = False, 
                   pattern: Optional[str] = None) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        List files with enhanced metadata and filtering.
        
        Args:
            directory: Directory to list (relative to base)
            include_dirs: Whether to include directories
            pattern: Optional regex pattern for filtering
            
        Returns:
            Tuple of (success, list of file metadata or error message)
        """
        start_time = time.time()
        success = False
        
        try:
            # Validate path
            if not self._is_path_safe(directory):
                return False, "Access denied: Invalid path"
            
            dir_path = os.path.normpath(os.path.join(self.base_dir, directory))
            
            if not os.path.exists(dir_path):
                return False, f"Directory not found: {directory}"
            
            if not os.path.isdir(dir_path):
                return False, f"Not a directory: {directory}"
            
            items = []
            pattern_re = re.compile(pattern) if pattern else None
            
            for item in os.listdir(dir_path):
                # Apply pattern filter if provided
                if pattern_re and not pattern_re.match(item):
                    continue
                
                item_path = os.path.join(dir_path, item)
                
                try:
                    stat = os.stat(item_path)
                    is_dir = os.path.isdir(item_path)
                    
                    if is_dir and not include_dirs:
                        continue
                    
                    # Get MIME type for files
                    mime_type = None
                    if not is_dir:
                        mime_type, _ = mimetypes.guess_type(item)
                    
                    metadata = {
                        "name": item,
                        "path": os.path.relpath(item_path, self.base_dir),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "type": "directory" if is_dir else "file",
                        "mime_type": mime_type,
                        "permissions": oct(stat.st_mode)[-3:] if hasattr(stat, 'st_mode') else None
                    }
                    
                    # Add checksum for files if available
                    if not is_dir:
                        checksum = self._file_checksums.get(item_path)
                        if checksum:
                            metadata["checksum"] = checksum
                    
                    items.append(metadata)
                    
                except (OSError, IOError) as e:
                    self.logger.warning(f"Could not stat {item}: {e}")
                    continue
            
            # Sort by name for consistency
            items.sort(key=lambda x: (x['type'] == 'file', x['name'].lower()))
            
            self.logger.info(f"Listed {len(items)} items in: {directory}")
            
            success = True
            return True, items
            
        except PermissionError:
            error_msg = f"Permission denied: {directory}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error listing files: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        finally:
            duration = time.time() - start_time
            self._track_operation('list', duration, success)

    def create_directory(self, directory_path: str, permissions: int = 0o755) -> Tuple[bool, str]:
        """
        Create a directory with specified permissions.
        
        Args:
            directory_path: Path of directory to create
            permissions: Unix-style permissions
            
        Returns:
            Tuple of (success, message)
        """
        start_time = time.time()
        success = False
        
        try:
            # Validate path
            if not self._is_path_safe(directory_path):
                return False, "Access denied: Invalid path"
            
            full_path = os.path.normpath(os.path.join(self.base_dir, directory_path))
            
            with self._lock:
                os.makedirs(full_path, exist_ok=True)
                
                # Set permissions on Unix-like systems
                if hasattr(os, 'chmod'):
                    os.chmod(full_path, permissions)
            
            self.logger.info(f"Directory created: {directory_path}")
            
            success = True
            return True, f"Directory created: {directory_path}"
            
        except PermissionError:
            error_msg = f"Permission denied: {directory_path}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error creating directory: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        finally:
            duration = time.time() - start_time
            self._track_operation('create_dir', duration, success)

    def delete_file(self, filename: str, move_to_archive: bool = True) -> Tuple[bool, str]:
        """
        Delete or archive a file.
        
        Args:
            filename: Name of file to delete
            move_to_archive: Whether to move to archive instead of permanent deletion
            
        Returns:
            Tuple of (success, message)
        """
        start_time = time.time()
        success = False
        
        try:
            # Validate path
            if not self._is_path_safe(filename):
                return False, "Access denied: Invalid path"
            
            file_path = os.path.normpath(os.path.join(self.base_dir, filename))
            
            if not os.path.exists(file_path):
                return False, f"File not found: {filename}"
            
            with self._lock:
                if move_to_archive:
                    # Move to archive with timestamp
                    archive_dir = os.path.join(self.base_dir, 'archive')
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    archive_name = f"{os.path.basename(filename)}_{timestamp}"
                    archive_path = os.path.join(archive_dir, archive_name)
                    
                    shutil.move(file_path, archive_path)
                    self.logger.info(f"File archived: {filename} -> {archive_name}")
                    message = f"File archived: {filename}"
                else:
                    # Permanent deletion
                    os.remove(file_path)
                    self.logger.info(f"File deleted: {filename}")
                    message = f"File deleted: {filename}"
                
                # Remove from cache
                if file_path in self._file_cache:
                    del self._file_cache[file_path]
                    del self._cache_access_times[file_path]
                
                # Remove checksum
                if file_path in self._file_checksums:
                    del self._file_checksums[file_path]
            
            success = True
            return True, message
            
        except PermissionError:
            error_msg = f"Permission denied: {filename}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error deleting file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        finally:
            duration = time.time() - start_time
            self._track_operation('delete', duration, success)

    def move_file(self, source: str, destination: str) -> Tuple[bool, str]:
        """
        Move a file to a new location.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate paths
            if not self._is_path_safe(source) or not self._is_path_safe(destination):
                return False, "Access denied: Invalid path"
            
            source_path = os.path.normpath(os.path.join(self.base_dir, source))
            dest_path = os.path.normpath(os.path.join(self.base_dir, destination))
            
            if not os.path.exists(source_path):
                return False, f"Source file not found: {source}"
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with self._lock:
                shutil.move(source_path, dest_path)
                
                # Update checksums
                if source_path in self._file_checksums:
                    self._file_checksums[dest_path] = self._file_checksums.pop(source_path)
            
            self.logger.info(f"File moved: {source} -> {destination}")
            return True, f"File moved successfully"
            
        except Exception as e:
            error_msg = f"Error moving file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def copy_file(self, source: str, destination: str) -> Tuple[bool, str]:
        """
        Copy a file to a new location.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate paths
            if not self._is_path_safe(source) or not self._is_path_safe(destination):
                return False, "Access denied: Invalid path"
            
            source_path = os.path.normpath(os.path.join(self.base_dir, source))
            dest_path = os.path.normpath(os.path.join(self.base_dir, destination))
            
            if not os.path.exists(source_path):
                return False, f"Source file not found: {source}"
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with self._lock:
                shutil.copy2(source_path, dest_path)
                
                # Copy checksum
                if source_path in self._file_checksums:
                    self._file_checksums[dest_path] = self._file_checksums[source_path]
            
            self.logger.info(f"File copied: {source} -> {destination}")
            return True, f"File copied successfully"
            
        except Exception as e:
            error_msg = f"Error copying file: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_file_info(self, filename: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
        """
        Get detailed information about a file.
        
        Args:
            filename: Name of file
            
        Returns:
            Tuple of (success, file info dict or error message)
        """
        try:
            # Validate path
            if not self._is_path_safe(filename):
                return False, "Access denied: Invalid path"
            
            file_path = os.path.normpath(os.path.join(self.base_dir, filename))
            
            if not os.path.exists(file_path):
                return False, f"File not found: {filename}"
            
            stat = os.stat(file_path)
            mime_type, encoding = mimetypes.guess_type(filename)
            
            info = {
                "name": os.path.basename(filename),
                "path": filename,
                "absolute_path": file_path,
                "size": stat.st_size,
                "size_human": self._format_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "type": "directory" if os.path.isdir(file_path) else "file",
                "mime_type": mime_type,
                "encoding": encoding,
                "permissions": oct(stat.st_mode)[-3:] if hasattr(stat, 'st_mode') else None,
                "checksum": self._file_checksums.get(file_path),
                "is_cached": file_path in self._file_cache,
                "access_count": len(self._access_log.get(filename, []))
            }
            
            return True, info
            
        except Exception as e:
            error_msg = f"Error getting file info: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def search_files(self, search_term: str, directory: str = "", 
                    file_types: Optional[List[str]] = None) -> Tuple[bool, Union[List[str], str]]:
        """
        Search for files matching criteria.
        
        Args:
            search_term: Term to search for in filenames
            directory: Directory to search in
            file_types: Optional list of file extensions to filter
            
        Returns:
            Tuple of (success, list of matching files or error message)
        """
        try:
            # Validate directory path
            if not self._is_path_safe(directory):
                return False, "Access denied: Invalid path"
            
            search_dir = os.path.join(self.base_dir, directory)
            if not os.path.exists(search_dir):
                return False, f"Directory not found: {directory}"
            
            matches = []
            search_pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            
            for root, dirs, files in os.walk(search_dir):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    # Check file extension if filter provided
                    if file_types:
                        ext = os.path.splitext(file)[1].lower()
                        if ext not in file_types:
                            continue
                    
                    # Search in filename
                    if search_pattern.search(file):
                        relative_path = os.path.relpath(
                            os.path.join(root, file), 
                            self.base_dir
                        )
                        matches.append(relative_path)
            
            self.logger.info(f"Search found {len(matches)} matches for '{search_term}'")
            return True, matches
            
        except Exception as e:
            error_msg = f"Error searching files: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance and usage metrics."""
        with self._lock:
            metrics = {
                "operations": dict(self._operation_metrics),
                "cache": {
                    "size": len(self._file_cache),
                    "max_size": self._max_cache_size,
                    "hit_rate": self._calculate_cache_hit_rate()
                },
                "checksums": len(self._file_checksums),
                "suspicious_events": len(self._suspicious_patterns),
                "total_files_tracked": len(self._access_log)
            }
            
            # Calculate average operation times
            for op, data in metrics["operations"].items():
                if data["count"] > 0:
                    data["average_time"] = data["total_time"] / data["count"]
                    data["error_rate"] = data["errors"] / data["count"]
            
            return metrics

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from recent operations."""
        # This is a simplified calculation
        total_reads = self._operation_metrics.get('read', {}).get('count', 0)
        if total_reads == 0:
            return 0.0
        
        # Estimate based on cache access patterns
        cache_hits = sum(1 for _ in self._cache_access_times.values())
        return min(cache_hits / max(total_reads, 1), 1.0)

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def cleanup(self):
        """Perform cleanup operations."""
        try:
            # Save checksums
            self._save_checksums()
            
            # Clear old archive files (optional)
            archive_dir = os.path.join(self.base_dir, 'archive')
            if os.path.exists(archive_dir):
                cutoff_date = datetime.now() - timedelta(days=30)
                for file in os.listdir(archive_dir):
                    file_path = os.path.join(archive_dir, file)
                    if os.path.getmtime(file_path) < cutoff_date.timestamp():
                        os.remove(file_path)
                        self.logger.info(f"Cleaned up old archive: {file}")
            
            self.logger.info("Cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass