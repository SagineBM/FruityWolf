"""
StatsService

Centralized service for gathering library statistics and metrics.
Keeps UI components "dumb" and reusable.
"""

import logging
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ..database import query, query_one
from ..scanner.library_scanner import get_sample_usage

logger = logging.getLogger(__name__)

class StatsService:
    """Service for retrieving library-wide statistics."""

    @staticmethod
    def get_sample_usage_stats(limit: int = 30) -> List[Dict[str, Any]]:
        """Get the most used samples across all projects."""
        try:
            return get_sample_usage(limit=limit)
        except Exception as e:
            logger.error(f"Error getting sample usage stats: {e}")
            return []

    @staticmethod
    def get_project_stage_counts() -> Dict[str, int]:
        """Get counts of projects in each classification stage."""
        try:
            rows = query("""
                SELECT state_id, COUNT(*) as count 
                FROM projects 
                GROUP BY state_id
            """)
            # Convert list of rows to dict
            counts = {row['state_id'] or 'UNKNOWN': row['count'] for row in rows}
            return counts
        except Exception as e:
            logger.error(f"Error getting project stage counts: {e}")
            return {}

    @staticmethod
    def get_library_overview() -> Dict[str, Any]:
        """Get high-level library metrics."""
        try:
            # Basic counts
            projects_count = query("SELECT COUNT(*) as count FROM projects")[0]['count']
            tracks_count = query("SELECT COUNT(*) as count FROM tracks")[0]['count']
            
            # Missing metadata
            missing_bpm = query("""
                SELECT COUNT(*) as count FROM tracks 
                WHERE bpm_user IS NULL AND bpm_detected IS NULL
            """)[0]['count']
            
            missing_key = query("""
                SELECT COUNT(*) as count FROM tracks 
                WHERE key_user IS NULL AND key_detected IS NULL
            """)[0]['count']

            # Rendered vs Non-rendered (approximate based on next_action)
            needs_render = query("""
                SELECT COUNT(*) as count FROM projects 
                WHERE next_action_id LIKE '%RENDER%'
            """)[0]['count']

            return {
                "total_projects": projects_count,
                "total_tracks": tracks_count,
                "missing_bpm": missing_bpm,
                "missing_key": missing_key,
                "needs_render": needs_render
            }
        except Exception as e:
            logger.error(f"Error getting library overview: {e}")
            return {}

    @staticmethod
    def get_recently_played_projects(limit: int = 5) -> List[Dict[str, Any]]:
        """Get the most recently played projects."""
        try:
            return query("""
                SELECT id, name, last_played_ts 
                FROM projects 
                WHERE last_played_ts IS NOT NULL 
                ORDER BY last_played_ts DESC 
                LIMIT ?
            """, (limit,))
        except Exception as e:
            logger.error(f"Error getting recently played projects: {e}")
            return []

    @staticmethod
    def get_extended_library_metrics() -> Dict[str, Any]:
        """Get high-level library metrics with health and trends."""
        overview = StatsService.get_library_overview()
        
        # Calculate health (dummy logic for now, could be based on missing metadata %)
        total = overview.get('total_tracks', 0)
        missing = (overview.get('missing_bpm', 0) + overview.get('missing_key', 0)) / 2
        health_score = max(0, 100 - (missing / total * 100)) if total > 0 else 100
        
        health_status = "Good"
        if health_score < 50: health_status = "Critical"
        elif health_score < 80: health_status = "Warning"

        return {
            "schema_version": "1.0",
            "health": {
                "score": health_score,
                "status": health_status,
                "label": f"Library Health: {health_status}"
            },
            "metrics": [
                {"label": "Total Samples", "value": str(overview.get('total_tracks', 0)), "icon": "audio", "color": "#8b5cf6"},
                {"label": "Unique Sounds", "value": str(overview.get('total_projects', 0)), "icon": "folder_open", "color": "#38bdf8"},
                {"label": "Needs Render", "value": str(overview.get('needs_render', 0)), "icon": "analyze", "color": "#facc15"},
                {"label": "Issues", "value": str(int(missing)), "icon": "alert", "color": "#ef4444"},
            ]
        }

    @staticmethod
    def get_overused_samples(limit: int = 5) -> List[Dict[str, Any]]:
        """Get samples used too frequently (or just the most used samples)."""
        raw_stats = StatsService.get_sample_usage_stats(limit=limit)
        total_projects = query_one("SELECT COUNT(*) as count FROM projects")['count'] or 1
        
        results = []
        for s in raw_stats:
            usage_pct = (s['count'] / total_projects) * 100
            # Fetch at least one valid path for previewing
            path_row = query_one("SELECT sample_path FROM project_samples WHERE sample_name = ? LIMIT 1", (s['sample_name'],))
            results.append({
                "id": s['sample_name'],
                "name": s['sample_name'],
                "usage_count": s['count'],
                "project_count": total_projects,
                "usage_pct": round(usage_pct, 1),
                "path": path_row['sample_path'] if path_row and path_row['sample_path'] else None
            })
        return results

    @staticmethod
    def get_underused_gems(limit: int = 5) -> List[Dict[str, Any]]:
        """Get samples used rarely but recently added or special."""
        rows = query("""
            SELECT ps.sample_name, ps.sample_path, COUNT(*) as count, MAX(p.updated_at) as last_used
            FROM project_samples ps
            JOIN projects p ON ps.project_id = p.id
            GROUP BY ps.sample_name
            HAVING count <= 2
            ORDER BY last_used DESC
            LIMIT ?
        """, (limit,))
        
        return [{
            "id": row['sample_name'],
            "name": row['sample_name'],
            "usage_count": row['count'],
            "last_used": datetime.fromtimestamp(row['last_used']).strftime("%Y-%m-%d") if row['last_used'] else "Unknown",
            "path": row['sample_path'] if row['sample_path'] else None
        } for row in rows]

    @staticmethod
    def get_sample_detail(sample_id: str) -> Dict[str, Any]:
        """Fetch full view-model for a sample detail page."""
        usage_rows = query("""
            SELECT ps.*, p.name as project_name, p.state_id, p.updated_at as project_ts
            FROM project_samples ps
            JOIN projects p ON ps.project_id = p.id
            WHERE ps.sample_name = ?
            ORDER BY p.updated_at DESC
        """, (sample_id,))

        if not usage_rows:
            return {"schema_version": "1.0", "error": "Not found"}

        projects = []
        timeline = []
        usage_count = len(usage_rows)
        sample_path = usage_rows[0]['sample_path']
        
        first_used = min(r['project_ts'] for r in usage_rows)
        last_used = max(r['project_ts'] for r in usage_rows)
        usage_span_days = (last_used - first_used) / 86400

        for r in usage_rows:
            p_date = datetime.fromtimestamp(r['project_ts'])
            
            # Find best render for this project
            render_row = query_one("""
                SELECT path FROM tracks 
                WHERE project_id = ? AND ext IN ('.wav', '.mp3')
                ORDER BY mtime DESC LIMIT 1
            """, (r['project_id'],))
            
            projects.append({
                "id": r['project_id'],
                "name": r['project_name'],
                "stage": r['state_id'],
                "date": p_date.strftime("%Y-%m-%d"),
                "ts": r['project_ts'],
                "render_path": render_row['path'] if render_row and render_row['path'] else None
            })
            timeline.append({
                "ts": r['project_ts'],
                "project_name": r['project_name'],
                "stage": r['state_id']
            })

        # Insights & Health
        insights = []
        health_score = 100
        
        total_projects = query_one("SELECT COUNT(*) as count FROM projects")['count'] or 1
        usage_pct = (usage_count / total_projects) * 100
        
        if usage_pct > 20:
            insights.append({"type": "warning", "text": "This sample dominates your library."})
            health_score -= 20
        
        recent_projs = query("SELECT id FROM projects ORDER BY updated_at DESC LIMIT 3")
        recent_ids = [rp['id'] for rp in recent_projs]
        used_in_recent = [r['project_id'] for r in usage_rows if r['project_id'] in recent_ids]
        if len(used_in_recent) >= 3:
             insights.append({"type": "danger", "text": "Monotony Risk: Used in all 3 most recent projects."})
             health_score -= 30

        if usage_count <= 2:
            insights.append({"type": "info", "text": "Underused Gem: Try using this in your next track."})

        return {
            "schema_version": "1.0",
            "health_score": max(0, health_score),
            "hero": {
                "name": sample_id,
                "usage_count": usage_count,
                "first_used": datetime.fromtimestamp(first_used).strftime("%b %Y"),
                "last_used": datetime.fromtimestamp(last_used).strftime("%b %Y"),
                "path": sample_path
            },
            "metrics": [
                {"label": "Project Count", "value": str(usage_count)},
                {"label": "Usage %", "value": f"{usage_pct:.1f}%"},
                {"label": "Last Project", "value": projects[0]['name'] if projects else "--"},
            ],
            "timeline": {
                "group_by": "week" if usage_span_days <= 60 else "month",
                "events": timeline
            },
            "projects": projects,
            "insights": insights
        }
