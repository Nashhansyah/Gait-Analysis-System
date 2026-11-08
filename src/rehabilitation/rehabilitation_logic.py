"""
Rehabilitation Logic Module
==========================
Handles aggregation of gait parameters across multiple sessions for trend analysis.
"""

import os
import json
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

class RehabilitationLogic:
    """
    Logic for aggregating and processing gait data across sessions.
    """
    
    def __init__(self, project_manager):
        """
        Initialize with a ProjectInputManager instance.
        
        Args:
            project_manager: Instance of ProjectInputManager
        """
        self.pm = project_manager
        
    def get_subject_sessions_data(self, subject_id: str) -> List[Dict]:
        """
        Get gait parameter data for all sessions of a subject.
        
        Args:
            subject_id: The ID of the subject
            
        Returns:
            List of dictionaries containing session info and gait parameters
        """
        sessions = self.pm.get_sessions(subject_id)
        aggregated_data = []
        
        for session in sessions:
            session_id = session['session_id']
            created_at = session.get('created_at', '')
            
            # Try to load gait parameters JSON first
            json_path = self.pm.get_output_file_path(subject_id, "gait_parameters", ".json", session_id)
            
            # If JSON doesn't exist, try CSV summary
            csv_path = self.pm.find_output_file(subject_id, "gait_parameters_summary", session_id)
            
            session_result = {
                "session_id": session_id,
                "date": created_at,
                "parameters": {}
            }
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        summary = data.get("summary", {}).get("overall", {})
                        # Also get step count from summary
                        step_info = data.get("summary", {}).get("step", {})
                        summary["step_count"] = step_info.get("count", 0)
                        session_result["parameters"] = summary
                except Exception as e:
                    print(f"Error loading {json_path}: {e}")
            elif csv_path and os.path.exists(csv_path):
                try:
                    df = pd.read_csv(csv_path)
                    # Convert CSV rows to dictionary (parameter, value)
                    summary = dict(zip(df['parameter'], df['value']))
                    
                    # Also get step count from step CSV file
                    step_csv_path = self.pm.find_output_file(subject_id, "gait_parameters_step", session_id)
                    if step_csv_path and os.path.exists(step_csv_path):
                        step_df = pd.read_csv(step_csv_path)
                        summary["step_count"] = len(step_df)
                    
                    session_result["parameters"] = summary
                except Exception as e:
                    print(f"Error loading {csv_path}: {e}")
            
            # Check if per-side ratios are missing and try to compute from cycle data
            params = session_result.get("parameters", {})
            if params and ("left_stance_ratio" not in params):
                cycle_csv_path = self.pm.find_output_file(subject_id, "gait_parameters_cycle", session_id)
                if cycle_csv_path and os.path.exists(cycle_csv_path):
                    try:
                        cycle_df = pd.read_csv(cycle_csv_path)
                        if not cycle_df.empty:
                            # Filter valid cycles ? cycle CSV usually contains all. 
                            # We can just average by side.
                            left_cycles = cycle_df[cycle_df['side'].str.lower() == 'left']
                            right_cycles = cycle_df[cycle_df['side'].str.lower() == 'right']
                            
                            if not left_cycles.empty:
                                params["left_stance_ratio"] = left_cycles['stance_ratio'].mean()
                                params["left_swing_ratio"] = left_cycles['swing_ratio'].mean()
                                
                            if not right_cycles.empty:
                                params["right_stance_ratio"] = right_cycles['stance_ratio'].mean()
                                params["right_swing_ratio"] = right_cycles['swing_ratio'].mean()
                            
                            session_result["parameters"] = params
                    except Exception as e:
                        print(f"Error computing from cycle CSV: {e}")

            aggregated_data.append(session_result)
            
        # Filter out sessions with no parameters and sort by date
        aggregated_data = [s for s in aggregated_data if s["parameters"]]
        aggregated_data.sort(key=lambda x: x["date"])
        
        return aggregated_data

    def prepare_plot_data(self, aggregated_data: List[Dict]) -> Dict[str, List]:
        """
        Transform aggregated data into formats suitable for Matplotlib plotting.
        
        Returns:
            Dictionary mapping parameter names to lists of values
        """
        plot_data = {
            "dates": [],
            "session_ids": [],
            "mean_walking_speed": [],
            "mean_cadence": [],
            "mean_stride_length": [],
            "mean_step_length": [],
            # Per-side ratios (clinical standard)
            "left_stance_ratio": [],
            "left_swing_ratio": [],
            "right_stance_ratio": [],
            "right_swing_ratio": [],
            # Combined ratios (backward compatibility)
            "mean_stance_ratio": [],
            "mean_swing_ratio": []
        }
        
        for entry in aggregated_data:
            # Format date for display
            try:
                dt = datetime.fromisoformat(entry["date"])
                date_str = dt.strftime("%Y-%m-%d\n%H:%M")
            except:
                date_str = entry["session_id"]
                
            plot_data["dates"].append(date_str)
            plot_data["session_ids"].append(entry["session_id"])
            
            params = entry["parameters"]
            plot_data["mean_walking_speed"].append(params.get("mean_walking_speed", 0))
            plot_data["mean_cadence"].append(params.get("mean_cadence", 0))
            plot_data["mean_stride_length"].append(params.get("mean_stride_length", 0))
            plot_data["mean_step_length"].append(params.get("mean_step_length", 0) * 100) # Convert to cm
            
            # Per-side ratios (clinical standard)
            plot_data["left_stance_ratio"].append(params.get("left_stance_ratio", 0) * 100)
            plot_data["left_swing_ratio"].append(params.get("left_swing_ratio", 0) * 100)
            plot_data["right_stance_ratio"].append(params.get("right_stance_ratio", 0) * 100)
            plot_data["right_swing_ratio"].append(params.get("right_swing_ratio", 0) * 100)
            
            # Combined ratios (backward compatibility)
            plot_data["mean_stance_ratio"].append(params.get("mean_stance_ratio", 0) * 100)
            plot_data["mean_swing_ratio"].append(params.get("mean_swing_ratio", 0) * 100)
            
        return plot_data

