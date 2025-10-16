# app/services/drivers_repo.py
from __future__ import annotations
from app.services.supabase import SupabaseClient

class DriversRepo:
    _cached_path: str | None = None

    @classmethod
    async def _path(cls) -> str:
        """Detect plural/singular path once."""
        if cls._cached_path:
            return cls._cached_path

        async with SupabaseClient().client() as c:
            r = await c.get("/drivers", params={"select": "id", "limit": "1"})
            if r.status_code == 404:
                r = await c.get("/driver", params={"select": "id", "limit": "1"})
                if r.status_code == 404:
                    raise RuntimeError("Neither table 'driver' nor 'drivers' exists.")
                cls._cached_path = "/driver"
            else:
                cls._cached_path = "/drivers"
        return cls._cached_path

    @staticmethod
    async def _select_id_by(c, path: str, **eq_filters) -> int | None:
        params = {"select": "id", "limit": "1"}
        for k, v in eq_filters.items():
            if v is not None:
                params[k] = f"eq.{v}"
        r = await c.get(path, params=params)
        if r.status_code >= 400:
            return None
        rows = r.json()
        if rows:
            try:
                return int(rows[0]["id"])
            except Exception:
                return None
        return None

    @classmethod
    async def ensure_driver_id(cls, name: str | None, phone: str | None) -> int:
        """
        Return an existing driver's id or create one.
        Match priority: phone_number (if provided) -> name -> insert.
        Always ensure a non-empty `name` on insert to satisfy NOT NULL constraints.
        """
        path = await cls._path()
        phone = (phone or "").strip() or None
        name = (name or "").strip() or None

      
        async with SupabaseClient().client() as c:
            if phone:
                found = await cls._select_id_by(c, path, phone_number=phone)
                if found is not None:
                    return found

            
            if name:
                found = await cls._select_id_by(c, path, name=name)
                if found is not None:
                    return found

           
            body = {"name": name or "Unknown"}
            if phone:
                body["phone_number"] = phone

           
            r = await c.post(path, json=body)
            if r.status_code >= 400:
                text = r.text
               
                if "42703" in text or "column" in text and "phone_number" in text and "does not exist" in text:
                    r = await c.post(path, json={"name": body["name"]})
               
                if r.status_code >= 400 and ("23502" in text or "null value in column \"name\"" in text):
                    r = await c.post(path, json={"name": "Unknown"})

                
                if r.status_code >= 400:
                    alt_path = "/driver" if path == "/driver" else "/drivers"
                    r = await c.post(alt_path, json={"name": body.get("name", "Unknown")})

                if r.status_code >= 400:
                    raise RuntimeError(f"{path} insert failed: {r.status_code} {r.text}")

            rows = r.json()
            return int(rows[0]["id"])
        
