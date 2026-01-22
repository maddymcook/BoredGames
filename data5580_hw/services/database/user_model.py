import logging

from flask import jsonify, request

from sqlalchemy.exc import IntegrityError
from data5580_hw.services.database_client import db
from data5580_hw.models.user_model import User as UserSQL
from data5580_hw.services.user import User


class UserController:    d
def __init__(self, user_service):
        self.user_service = user_service    
def create_user(self, data):
        name = data.get("username")
        email = data.get("email")

        if not name or not email:
            return {"error": "Missing values"}, 400

        user = self.user_service.create_user(name, email)
        if not user:
            return {"error": "Email already exists"}, 400

        return {
            "username": user.name,
            "email": user.email
        }, 200
