"""
Project Input Manager
=====================
Manages project initialization, subject identification, and video acquisition.
This module handles:
- Subject ID validation and project creation
- Multi-session support per subject
- Video file browsing or camera recording
- Folder structure setup for downstream pipeline
- Metadata generation and storage
"""

import os
import json
import shutil
from datetime import datetime
from typing import Optional, Dict, Tuple, List
import cv2


class ProjectInputManager:
    """
    Manages the initialization of gait analysis projects.
    
    Responsibilities:
    - Create project folder structure
    - Manage multiple sessions per subject
    - Acquire video (browse or record)
    - Save project metadata
    
    Session Structure:
    - Each subject can have multiple sessions
    - Each session has its own video and pipeline progress
    - Legacy data without sessions is treated as having a "default" session
    """
    
    DEFAULT_SESSION_ID = "default"
    
    def __init__(self, base_data_path: str = "data"):
        """
        Initialize the Project Input Manager.
        
        Args:
            base_data_path: Base path for all data storage
        """
        self.base_data_path = os.path.abspath(base_data_path)
        self.current_subject_id: Optional[str] = None
        self.current_session_id: Optional[str] = None
        self.current_project_path: Optional[str] = None
        self.metadata: Dict = {}
        
    def validate_subject_id(self, subject_id: str, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate subject ID format. For new sessions, allows existing subjects.
        
        Args:
            subject_id: Proposed subject identifier
            session_id: Optional session ID (if None, checks for new subject)
            
        Returns:
            Tuple of (is_valid, message)
        """
        # Check if empty
        if not subject_id or not subject_id.strip():
            return False, "Subject ID cannot be empty"
        
        # Clean up
        subject_id = subject_id.strip()
        
        # Check format (alphanumeric and underscores only)
        if not all(c.isalnum() or c == '_' for c in subject_id):
            return False, "Subject ID can only contain letters, numbers, and underscores"
        
        # If session_id is provided, allow existing subjects (adding new session)
        if session_id:
            # Validate session_id format
            if not all(c.isalnum() or c == '_' for c in session_id):
                return False, "Session ID can only contain letters, numbers, and underscores"
            
            # Check if session already exists
            if self.session_exists(subject_id, session_id):
                return False, f"Session '{session_id}' already exists for subject '{subject_id}'"
            
            return True, "Valid subject and session ID"
        
        # For new subject without session_id, check for duplicates (legacy behavior)
        metadata_path = os.path.join(self.base_data_path, "metadata", f"{subject_id}_project.json")
        if os.path.exists(metadata_path):
            return False, f"Subject '{subject_id}' already exists. Use session ID to add new session."
        
        return True, "Valid subject ID"
    
    def session_exists(self, subject_id: str, session_id: str) -> bool:
        """
        Check if a session exists for the subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier
            
        Returns:
            True if session exists
        """
        # Check in metadata
        success, _, metadata = self.load_project(subject_id, set_current=False)
        if not success:
            return False
        
        sessions = metadata.get("sessions", {})
        return session_id in sessions
    
    def get_sessions(self, subject_id: str) -> List[Dict]:
        """
        Get all sessions for a subject.
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            List of session dictionaries with session_id and info
        """
        success, _, metadata = self.load_project(subject_id, set_current=False)
        if not success:
            return []
        
        sessions = metadata.get("sessions", {})
        
        # Legacy data without sessions - treat as default session
        if not sessions:
            return [{
                "session_id": self.DEFAULT_SESSION_ID,
                "created_at": metadata.get("created_at", ""),
                "video_path": metadata.get("video_path", ""),
                "pipeline_status": metadata.get("pipeline_status", {}),
                "is_legacy": True
            }]
        
        result = []
        for session_id, session_data in sessions.items():
            session_info = {
                "session_id": session_id,
                **session_data,
                "is_legacy": False
            }
            result.append(session_info)
        
        return sorted(result, key=lambda x: x.get("created_at", ""))
    
    def get_current_session(self) -> Optional[str]:
        """Get the current active session ID."""
        return self.current_session_id
    
    def set_current_session(self, subject_id: str, session_id: str) -> bool:
        """
        Set the current active session.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier
            
        Returns:
            True if session was set successfully
        """
        # For legacy data, allow "default" session
        if session_id == self.DEFAULT_SESSION_ID:
            self.current_subject_id = subject_id
            self.current_session_id = session_id
            return True
        
        if not self.session_exists(subject_id, session_id):
            return False
        
        self.current_subject_id = subject_id
        self.current_session_id = session_id
        return True
    
    def create_project_structure(self, subject_id: str, session_id: Optional[str] = None) -> Dict[str, str]:
        """
        Create folder structure for a subject/session.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (None for legacy behavior)
            
        Returns:
            Dictionary of created folder paths
        """
        # Use default session if not specified
        if session_id is None:
            session_id = self.DEFAULT_SESSION_ID
        
        # Paths that include session (video, openpose, and gait_parameters need session subdirectory)
        folders = {
            "input_video": os.path.join(self.base_data_path, "input_video", subject_id, session_id),
            "openpose_raw": os.path.join(self.base_data_path, "openpose_raw", subject_id, session_id),
            "correction_legid": os.path.join(self.base_data_path, "correction_legid"),
            "scaled_pose": os.path.join(self.base_data_path, "scaled_pose"),
            "preprocessed_signal": os.path.join(self.base_data_path, "preprocessed_signal"),
            "gait_events": os.path.join(self.base_data_path, "gait_events"),
            "gait_parameters": os.path.join(self.base_data_path, "gait_parameters", subject_id, session_id),
            "metadata": os.path.join(self.base_data_path, "metadata"),
        }
        
        # Create all folders
        for folder_path in folders.values():
            os.makedirs(folder_path, exist_ok=True)
        
        self.current_subject_id = subject_id
        self.current_session_id = session_id
        self.current_project_path = folders["input_video"]
        
        return folders
    
    def browse_video(self, source_path: str, subject_id: str, 
                     session_id: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """
        Copy a video file to the project folder.
        
        Args:
            source_path: Path to source video file
            subject_id: Subject identifier
            session_id: Session identifier (None for new default session)
            
        Returns:
            Tuple of (success, message, video_info)
        """
        # Validate file exists
        if not os.path.exists(source_path):
            return False, "Video file not found", {}
        
        # Validate extension
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        ext = os.path.splitext(source_path)[1].lower()
        if ext not in valid_extensions:
            return False, f"Invalid video format. Supported: {valid_extensions}", {}
        
        # Get video info
        video_info = self._get_video_info(source_path)
        if not video_info:
            return False, "Could not read video file", {}
        
        # Create project structure
        folders = self.create_project_structure(subject_id, session_id)
        
        # Copy video to project folder
        dest_path = os.path.join(folders["input_video"], "video_raw.mp4")
        
        # If not mp4, we still copy with mp4 extension (OpenPose handles various formats)
        shutil.copy2(source_path, dest_path)
        
        video_info["path"] = dest_path
        video_info["source"] = "browse"
        video_info["original_path"] = source_path
        
        return True, "Video imported successfully", video_info
    
    def record_video(self, subject_id: str, camera_index: int = 0, 
                     duration: Optional[float] = None,
                     session_id: Optional[str] = None) -> Tuple[bool, str, Dict]:
        """
        Record video from camera.
        
        Args:
            subject_id: Subject identifier
            camera_index: Camera device index
            duration: Recording duration in seconds (None = manual stop)
            session_id: Session identifier
            
        Returns:
            Tuple of (success, message, video_info)
        """
        # Create project structure first
        folders = self.create_project_structure(subject_id, session_id)
        dest_path = os.path.join(folders["input_video"], "video_raw.mp4")
        
        # Open camera
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return False, f"Could not open camera {camera_index}", {}
        
        # Get camera properties
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(dest_path, fourcc, fps, (width, height))
        
        frame_count = 0
        start_time = datetime.now()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                out.write(frame)
                frame_count += 1
                
                # Check duration limit
                if duration:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    if elapsed >= duration:
                        break
                        
        finally:
            cap.release()
            out.release()
        
        video_info = {
            "path": dest_path,
            "source": "camera",
            "fps": fps,
            "width": width,
            "height": height,
            "frame_count": frame_count,
            "duration": frame_count / fps if fps > 0 else 0
        }
        
        return True, "Video recorded successfully", video_info
    
    def _get_video_info(self, video_path: str) -> Optional[Dict]:
        """
        Extract video information using OpenCV.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with video properties or None if failed
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            return {
                "fps": fps,
                "width": width,
                "height": height,
                "frame_count": frame_count,
                "duration": duration,
                "resolution": f"{width}x{height}"
            }
        finally:
            cap.release()
    
    def save_metadata(self, subject_id: str, video_info: Dict, 
                      notes: str = "", session_id: Optional[str] = None) -> str:
        """
        Save project metadata to JSON file.
        
        Args:
            subject_id: Subject identifier
            video_info: Video information dictionary
            notes: Optional notes about the subject/session
            session_id: Session identifier
            
        Returns:
            Path to saved metadata file
        """
        if session_id is None:
            session_id = self.DEFAULT_SESSION_ID
        
        metadata_path = os.path.join(
            self.base_data_path, "metadata", f"{subject_id}_project.json"
        )
        
        # Load existing metadata if exists
        existing_metadata = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    existing_metadata = json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Create session data
        session_data = {
            "video_path": video_info.get("path", ""),
            "video_source": video_info.get("source", "unknown"),
            "fps": video_info.get("fps", 0),
            "resolution": video_info.get("resolution", ""),
            "frame_count": video_info.get("frame_count", 0),
            "duration": video_info.get("duration", 0),
            "created_at": datetime.now().isoformat(),
            "notes": notes,
            "pipeline_status": {
                "project_input": "completed",
                "openpose": "pending",
                "correction_legid": "pending",
                "scaling": "pending",
                "signal_preprocessing": "pending",
                "gait_event": "pending",
                "gait_parameter": "pending"
            }
        }
        
        # Initialize or update sessions
        if "sessions" not in existing_metadata:
            existing_metadata["sessions"] = {}
        
        existing_metadata["sessions"][session_id] = session_data
        
        # Update top-level metadata
        metadata = {
            "subject_id": subject_id,
            "created_at": existing_metadata.get("created_at", datetime.now().isoformat()),
            "last_updated": datetime.now().isoformat(),
            "sessions": existing_metadata["sessions"],
            # Keep legacy fields for backward compatibility
            "video_path": session_data["video_path"],
            "video_source": session_data["video_source"],
            "fps": session_data["fps"],
            "resolution": session_data["resolution"],
            "frame_count": session_data["frame_count"],
            "duration": session_data["duration"],
            "notes": notes,
            "pipeline_status": session_data["pipeline_status"],
            "current_session": session_id
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        self.metadata = metadata
        self.current_session_id = session_id
        return metadata_path
    
    def load_project(self, subject_id: str, session_id: Optional[str] = None, 
                     set_current: bool = True) -> Tuple[bool, str, Dict]:
        """
        Load an existing project by subject ID.
        
        Args:
            subject_id: Subject identifier
            session_id: Optional specific session to load
            set_current: Whether to set this as the current active project/session
            
        Returns:
            Tuple of (success, message, metadata)
        """
        metadata_path = os.path.join(
            self.base_data_path, "metadata", f"{subject_id}_project.json"
        )
        
        if not os.path.exists(metadata_path):
            return False, f"Project '{subject_id}' not found", {}
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            if set_current:
                self.current_subject_id = subject_id
                
                # Handle session selection
                if session_id:
                    self.current_session_id = session_id
                elif "current_session" in metadata:
                    self.current_session_id = metadata["current_session"]
                else:
                    # Legacy data - use default
                    self.current_session_id = self.DEFAULT_SESSION_ID
                
                self.metadata = metadata
            
            return True, "Project loaded successfully", metadata
            
        except json.JSONDecodeError:
            return False, "Corrupted project metadata", {}
    
    def update_pipeline_status(self, subject_id: str, stage: str, 
                                status: str, session_id: Optional[str] = None) -> bool:
        """
        Update the pipeline status for a subject/session.
        
        Args:
            subject_id: Subject identifier
            stage: Pipeline stage name
            status: New status ('pending', 'running', 'completed', 'failed')
            session_id: Session identifier (None uses current session)
            
        Returns:
            Success boolean
        """
        metadata_path = os.path.join(
            self.base_data_path, "metadata", f"{subject_id}_project.json"
        )
        
        if not os.path.exists(metadata_path):
            return False
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Use provided session or current session
            target_session = session_id or self.current_session_id or self.DEFAULT_SESSION_ID
            
            # Update session-specific status if sessions exist
            if "sessions" in metadata and target_session in metadata["sessions"]:
                if "pipeline_status" not in metadata["sessions"][target_session]:
                    metadata["sessions"][target_session]["pipeline_status"] = {}
                metadata["sessions"][target_session]["pipeline_status"][stage] = status
            
            # Also update legacy top-level for backward compatibility
            if "pipeline_status" not in metadata:
                metadata["pipeline_status"] = {}
            metadata["pipeline_status"][stage] = status
            metadata["last_updated"] = datetime.now().isoformat()
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception:
            return False
    
    def get_existing_subjects(self) -> list:
        """
        Get list of existing subject IDs.
        
        Returns:
            List of subject ID strings
        """
        metadata_folder = os.path.join(self.base_data_path, "metadata")
        
        if not os.path.exists(metadata_folder):
            return []
        
        subjects = []
        for filename in os.listdir(metadata_folder):
            if filename.endswith("_project.json"):
                subject_id = filename.replace("_project.json", "")
                subjects.append(subject_id)
        
        return sorted(subjects)
    
    def get_video_path(self, subject_id: str, session_id: Optional[str] = None) -> Optional[str]:
        """
        Get the video path for a subject/session.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (None uses current or tries legacy path)
            
        Returns:
            Video file path or None
        """
        # Use provided session, current session, or default
        target_session = session_id or self.current_session_id
        
        # Try session-aware path first
        if target_session:
            video_path = os.path.join(
                self.base_data_path, "input_video", subject_id, target_session, "video_raw.mp4"
            )
            if os.path.exists(video_path):
                return video_path
        
        # Fallback to legacy path (no session subfolder)
        legacy_path = os.path.join(
            self.base_data_path, "input_video", subject_id, "video_raw.mp4"
        )
        if os.path.exists(legacy_path):
            return legacy_path
        
        return None
    
    def get_openpose_output_path(self, subject_id: str, session_id: Optional[str] = None) -> str:
        """
        Get the OpenPose output folder path for a subject/session.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (None uses current session)
            
        Returns:
            OpenPose output folder path
        """
        target_session = session_id or self.current_session_id
        
        # Try session-aware path first
        if target_session:
            session_path = os.path.join(self.base_data_path, "openpose_raw", subject_id, target_session)
            # Check if session folder exists or if we're creating a new session
            if os.path.exists(session_path) or target_session != self.DEFAULT_SESSION_ID:
                return session_path
        
        # Fallback to legacy path
        return os.path.join(self.base_data_path, "openpose_raw", subject_id)

    def get_gait_parameters_output_dir(self, subject_id: str, session_id: Optional[str] = None) -> str:
        """
        Get the gait parameters output directory path for a subject/session.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (None uses current session)
            
        Returns:
            Directory path: data/gait_parameters/{subject_id}/{session_id}
        """
        target_session = session_id or self.current_session_id or self.DEFAULT_SESSION_ID
        folder = os.path.join(self.base_data_path, "gait_parameters", subject_id, target_session)
        os.makedirs(folder, exist_ok=True)
        return folder

    def get_openpose_frames_output_dir(self, subject_id: str, session_id: Optional[str] = None) -> str:
        """
        Get the dedicated output directory path for high-resolution OpenPose per-frame photos.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (None uses current session)
            
        Returns:
            Directory path: data/openpose_frames/{subject_id}/{session_id}
        """
        target_session = session_id or self.current_session_id or self.DEFAULT_SESSION_ID
        folder = os.path.join(self.base_data_path, "openpose_frames", subject_id, target_session)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    def get_output_file_path(self, subject_id: str, output_type: str, 
                             extension: str, session_id: Optional[str] = None) -> str:
        """
        Get the output file path for a subject/session.
        
        Args:
            subject_id: Subject identifier
            output_type: Type of output ('correction_legid', 'scaled_pose', etc.)
            extension: File extension (e.g., '.json', '.csv')
            session_id: Session identifier (None uses current session)
            
        Returns:
            Output file path
        """
        target_session = session_id or self.current_session_id or self.DEFAULT_SESSION_ID
        
        # Map output types to folder names and file suffixes
        type_mapping = {
            "correction_legid": ("correction_legid", "_corrected.json"),
            "scaled_pose": ("scaled_pose", "_scaled.json"),
            "preprocessed_signal": ("preprocessed_signal", "_signal.json"),
            "gait_events": ("gait_events", "_events.json"),
            "gait_parameters_step": ("gait_parameters", "_step.csv"),
            "gait_parameters_cycle": ("gait_parameters", "_cycle.csv"),
            "gait_parameters_summary": ("gait_parameters", "_summary.csv"),
        }
        
        if output_type in type_mapping:
            folder, suffix = type_mapping[output_type]
            # Include session in filename
            if target_session != self.DEFAULT_SESSION_ID:
                filename = f"{subject_id}_{target_session}{suffix}"
            else:
                filename = f"{subject_id}{suffix}"
            return os.path.join(self.base_data_path, folder, filename)
        
        # Default fallback
        return os.path.join(self.base_data_path, output_type, f"{subject_id}{extension}")
    
    def find_output_file(self, subject_id: str, output_type: str, 
                         session_id: Optional[str] = None) -> Optional[str]:
        """
        Find an existing output file, checking both session-aware and legacy paths.
        
        Args:
            subject_id: Subject identifier
            output_type: Type of output
            session_id: Session identifier
            
        Returns:
            Path if file exists, None otherwise
        """
        target_session = session_id or self.current_session_id or self.DEFAULT_SESSION_ID
        
        # Type mapping
        type_mapping = {
            "correction_legid": ("correction_legid", "_corrected.json"),
            "scaled_pose": ("scaled_pose", "_scaled.json"),
            "preprocessed_signal": ("preprocessed_signal", "_signal.json"),
            "gait_events": ("gait_events", "_events.json"),
            "gait_parameters_step": ("gait_parameters", "_step.csv"),
            "gait_parameters_cycle": ("gait_parameters", "_cycle.csv"),
            "gait_parameters_summary": ("gait_parameters", "_summary.csv"),
        }
        
        if output_type not in type_mapping:
            return None
        
        folder, suffix = type_mapping[output_type]
        
        # Try session-aware path first
        if target_session != self.DEFAULT_SESSION_ID:
            session_path = os.path.join(
                self.base_data_path, folder, f"{subject_id}_{target_session}{suffix}"
            )
            if os.path.exists(session_path):
                return session_path
        
        # Try legacy path
        legacy_path = os.path.join(self.base_data_path, folder, f"{subject_id}{suffix}")
        if os.path.exists(legacy_path):
            return legacy_path
        
        return None
    
    def delete_project(self, subject_id: str, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Delete a project or a specific session.
        
        Args:
            subject_id: Subject identifier to delete
            session_id: If provided, only delete this session. If None, delete entire subject.
            
        Returns:
            Tuple of (success, message)
        """
        deleted_items = []
        errors = []
        
        if session_id and session_id != self.DEFAULT_SESSION_ID:
            # Delete only specific session
            return self._delete_session(subject_id, session_id)
        
        # Delete entire subject (all sessions)
        
        # Folders to check and delete (including session subfolders)
        folders_to_delete = [
            os.path.join(self.base_data_path, "input_video", subject_id),
            os.path.join(self.base_data_path, "openpose_raw", subject_id),
        ]
        
        # Files to check and delete (both legacy and session-aware)
        files_to_delete = [
            os.path.join(self.base_data_path, "metadata", f"{subject_id}_project.json"),
        ]
        
        # Find all session files
        success, _, metadata = self.load_project(subject_id)
        sessions = [self.DEFAULT_SESSION_ID]
        if success and "sessions" in metadata:
            sessions = list(metadata["sessions"].keys())
        
        for sess in sessions:
            suffix = "" if sess == self.DEFAULT_SESSION_ID else f"_{sess}"
            files_to_delete.extend([
                os.path.join(self.base_data_path, "correction_legid", f"{subject_id}{suffix}_corrected.json"),
                os.path.join(self.base_data_path, "scaled_pose", f"{subject_id}{suffix}_scaled.json"),
                os.path.join(self.base_data_path, "preprocessed_signal", f"{subject_id}{suffix}_signal.json"),
                os.path.join(self.base_data_path, "gait_events", f"{subject_id}{suffix}_events.json"),
                os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}{suffix}_step.csv"),
                os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}{suffix}_cycle.csv"),
                os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}{suffix}_summary.csv"),
            ])
        
        # Also add legacy file patterns
        files_to_delete.extend([
            os.path.join(self.base_data_path, "correction_legid", f"{subject_id}_corrected.json"),
            os.path.join(self.base_data_path, "scaled_pose", f"{subject_id}_scaled.json"),
            os.path.join(self.base_data_path, "preprocessed_signal", f"{subject_id}_signal.json"),
            os.path.join(self.base_data_path, "gait_events", f"{subject_id}_events.json"),
            os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}_step.csv"),
            os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}_cycle.csv"),
            os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}_summary.csv"),
        ])
        
        # Delete folders
        for folder in folders_to_delete:
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder)
                    deleted_items.append(folder)
                except Exception as e:
                    errors.append(f"Failed to delete {folder}: {str(e)}")
        
        # Delete files
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_items.append(file_path)
                except Exception as e:
                    errors.append(f"Failed to delete {file_path}: {str(e)}")
        
        # Clear current project if it was deleted
        if self.current_subject_id == subject_id:
            self.current_subject_id = None
            self.current_session_id = None
            self.current_project_path = None
            self.metadata = {}
        
        if errors:
            return False, f"Some files could not be deleted: {'; '.join(errors)}"
        
        if not deleted_items:
            return False, f"Project '{subject_id}' not found"
        
        return True, f"Project '{subject_id}' deleted successfully ({len(deleted_items)} items removed)"
    
    def _delete_session(self, subject_id: str, session_id: str) -> Tuple[bool, str]:
        """
        Delete a specific session from a subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier to delete
            
        Returns:
            Tuple of (success, message)
        """
        deleted_items = []
        errors = []
        
        # Load metadata
        success, _, metadata = self.load_project(subject_id)
        if not success:
            return False, f"Subject '{subject_id}' not found"
        
        if "sessions" not in metadata or session_id not in metadata["sessions"]:
            return False, f"Session '{session_id}' not found for subject '{subject_id}'"
        
        # Folders to delete
        folders_to_delete = [
            os.path.join(self.base_data_path, "input_video", subject_id, session_id),
            os.path.join(self.base_data_path, "openpose_raw", subject_id, session_id),
        ]
        
        # Files to delete
        suffix = f"_{session_id}"
        files_to_delete = [
            os.path.join(self.base_data_path, "correction_legid", f"{subject_id}{suffix}_corrected.json"),
            os.path.join(self.base_data_path, "scaled_pose", f"{subject_id}{suffix}_scaled.json"),
            os.path.join(self.base_data_path, "preprocessed_signal", f"{subject_id}{suffix}_signal.json"),
            os.path.join(self.base_data_path, "gait_events", f"{subject_id}{suffix}_events.json"),
            os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}{suffix}_step.csv"),
            os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}{suffix}_cycle.csv"),
            os.path.join(self.base_data_path, "gait_parameters", f"{subject_id}{suffix}_summary.csv"),
        ]
        
        # Delete folders
        for folder in folders_to_delete:
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder)
                    deleted_items.append(folder)
                except Exception as e:
                    errors.append(f"Failed to delete {folder}: {str(e)}")
        
        # Delete files
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_items.append(file_path)
                except Exception as e:
                    errors.append(f"Failed to delete {file_path}: {str(e)}")
        
        # Remove session from metadata
        del metadata["sessions"][session_id]
        
        # Update current session if deleted
        if metadata["sessions"]:
            # Set to another session
            remaining_sessions = list(metadata["sessions"].keys())
            metadata["current_session"] = remaining_sessions[0]
        else:
            metadata["current_session"] = self.DEFAULT_SESSION_ID
        
        metadata["last_updated"] = datetime.now().isoformat()
        
        # Save updated metadata
        metadata_path = os.path.join(
            self.base_data_path, "metadata", f"{subject_id}_project.json"
        )
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        if self.current_subject_id == subject_id and self.current_session_id == session_id:
            self.current_session_id = metadata["current_session"]
        
        if errors:
            return False, f"Some files could not be deleted: {'; '.join(errors)}"
        
        return True, f"Session '{session_id}' deleted successfully ({len(deleted_items)} items removed)"
