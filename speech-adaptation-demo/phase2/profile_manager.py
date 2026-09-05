import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from .db import Profile, get_session


class ProfileManager:
    def create_profile(self, name: str, characteristics: Dict) -> str:
        session = get_session()
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        profile_data = {
            "user_id": user_id,
            "name": name,
            "speech_characteristics": characteristics or {},
            "custom_vocabulary": [],
            "pronunciation_map": {},
            "model_preferences": {
                "preferred_asr": "deepgram",
                "ensemble_enabled": False,
            },
            "performance_history": {
                "wer_over_time": [],
                "semscore_over_time": [],
            },
        }
        try:
            session.add(
                Profile(
                    user_id=user_id,
                    name=name,
                    created_at=datetime.utcnow(),
                    profile_data=profile_data,
                )
            )
            session.commit()
            return user_id
        finally:
            session.close()

    def load_profile(self, user_id: str) -> Optional[Dict]:
        session = get_session()
        try:
            row = session.query(Profile).filter(Profile.user_id == user_id).one_or_none()
            return row.profile_data if row else None
        finally:
            session.close()

    def save_profile(self, profile_data: Dict):
        session = get_session()
        try:
            row = session.query(Profile).filter(Profile.user_id == profile_data["user_id"]).one_or_none()
            if row:
                row.name = profile_data.get("name", row.name)
                row.profile_data = profile_data
            else:
                session.add(
                    Profile(
                        user_id=profile_data["user_id"],
                        name=profile_data.get("name", "Unknown"),
                        profile_data=profile_data,
                    )
                )
            session.commit()
        finally:
            session.close()

    def update_preferences(self, user_id: str, prefs: Dict):
        profile = self.load_profile(user_id)
        if not profile:
            return
        profile["model_preferences"].update(prefs)
        self.save_profile(profile)

    def export_profile(self, user_id: str, file_path: str):
        profile = self.load_profile(user_id)
        if not profile:
            return
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)

    def import_profile(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
        self.save_profile(profile)
        return profile["user_id"]

    def list_profiles(self) -> List[Dict]:
        session = get_session()
        try:
            rows = session.query(Profile).all()
            return [{"user_id": r.user_id, "name": r.name} for r in rows]
        finally:
            session.close()
