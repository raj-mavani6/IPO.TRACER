from pymongo import MongoClient
import os

class Database:
    def __init__(self, uri="mongodb://localhost:27017/", db_name="ipo_database"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db['ipo_records']
        self.list_collection = self.db['List']

    def normalize_name(self, name):
        if not name: return ""
        # Remove common suffixes and punctuation, lowercase
        n = name.lower()
        # Remove Investorgain specific markers like ' BSE SME U', ' IPO O', ' L@178.00', etc.
        patterns = [
            r' limited', r' ltd', r' bse sme', r' nse sme', r' ipo',
            r' [ouc]$', r' l$', r' l[@#].*', r'\(.*\)'
        ]
        import re
        for p in patterns:
            n = re.sub(p, '', n)
            
        n = n.replace(".", "").replace(",", "").replace("-", " ")
        return " ".join(n.split())

    def upsert_ipo(self, name, data):
        """
        Updates an existing IPO record or inserts a new one if it doesn't exist.
        Uses a normalized version of the name to prevent duplicates from different sources.
        """
        normalized = self.normalize_name(name)
        # We store the original name in the document too, but use normalized as the pivot
        query = {"normalized_name": normalized}
        
        # Ensure the document has the normalized name and original name
        data["normalized_name"] = normalized
        if "ipo_name" not in data:
            data["ipo_name"] = name
            
        update = {"$set": data}
        result = self.collection.update_one(query, update, upsert=True)
        return "Updated" if result.matched_count > 0 else "Inserted"

    def upsert_list_record(self, name, data):
        """
        Updates an existing IPO record in the 'List' collection or inserts a new one.
        """
        normalized = self.normalize_name(name)
        query = {"normalized_name": normalized}
        data["normalized_name"] = normalized
        if "name" not in data:
            data["name"] = name
            
        update = {"$set": data}
        result = self.list_collection.update_one(query, update, upsert=True)
        return "Updated" if result.matched_count > 0 else "Inserted"

    def get_all_ipos(self):
        return list(self.collection.find({}, {'_id': 0}))

    def get_ipo_by_name(self, name):
        """
        Tries to find an IPO by exact name or normalized name.
        """
        # 1. Try exact match in main records
        res = self.collection.find_one({"ipo_name": name}, {'_id': 0})
        if res: return res
        
        # 2. Try normalized match in main records
        norm = self.normalize_name(name)
        res = self.collection.find_one({"normalized_name": norm}, {'_id': 0})
        if res: return res
        
        # 3. Last fallback: Try exact name in List collection
        res = self.list_collection.find_one({"name": name}, {'_id': 0})
        if res:
            if "last_updated" not in res:
                res["last_updated"] = res.get("timestamp", "N/A")
            return res
        return None

    def get_all_list_records(self):
        """Fetch all records from the clean 'List' collection."""
        return list(self.list_collection.find({}, {'_id': 0}))
