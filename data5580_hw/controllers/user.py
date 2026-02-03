import logging

from flask import jsonify, request

from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from data5580_hw.services.database.database_client import db
from data5580_hw.services.database.user_model import UserSQL
from data5580_hw.models.user import User, UserUpdate

logger = logging.getLogger(__name__)


def _validation_error_message(e: ValidationError) -> str:
    """Return a specific message for validation failures (e.g. invalid email)."""
    for err in e.errors():
        if "email" in str(err.get("loc", [])).lower():
            return "Invalid email format"
        if "name" in str(err.get("loc", [])).lower():
            return "Invalid or missing name"
    return "Validation failed: " + str(e.errors())


class UserController:
    @staticmethod
    def create_user():
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            user = User.model_validate(data)
        except ValidationError as e:
            return jsonify({"error": _validation_error_message(e)}), 400

        user_sql = UserSQL(name=user.name, email=user.email, id=user.id)
        db.session.add(user_sql)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "email is already in use"}), 400

        logger.info("user created, %s for %s", user.id, user.email)
        return jsonify(user.model_dump()), 200

    @staticmethod
    def get_user_by_id(user_id: str):
        logger.debug("Got user_id %s", user_id)
        user_sql = db.session.query(UserSQL).filter(UserSQL.id == user_id).first()
        if not user_sql:
            return jsonify({"error": "User not found"}), 404

        user = User.model_validate(user_sql, from_attributes=True)
        logger.info("User retrieved, %s", user_id)
        return jsonify(user.model_dump()), 200

    @staticmethod
    def list_users():
        users_sql = db.session.query(UserSQL).all()
        users = [User.model_validate(u, from_attributes=True).model_dump() for u in users_sql]
        return jsonify(users), 200

    @staticmethod
    def update_user(user_id: str):
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            payload = UserUpdate.model_validate(data)
        except ValidationError as e:
            msg = "Missing or invalid fields"
            for err in e.errors():
                loc = err.get("loc", [])
                if loc:
                    msg += f": {loc[0]}"
                break
            return jsonify({"error": msg}), 400

        user_sql = db.session.query(UserSQL).filter(UserSQL.id == user_id).first()
        if not user_sql:
            return jsonify({"error": "User not found"}), 404

        if payload.name is not None:
            user_sql.name = payload.name
        if payload.email is not None:
            user_sql.email = payload.email
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "email is already in use"}), 400

        user = User.model_validate(user_sql, from_attributes=True)
        return jsonify({
            "message": "User details updated successfully.",
            "user": user.model_dump()
        }), 200

    @staticmethod
    def delete_user(user_id: str):
        user_sql = db.session.query(UserSQL).filter(UserSQL.id == user_id).first()
        if not user_sql:
            return jsonify({"error": "User not found"}), 404
        db.session.delete(user_sql)
        db.session.commit()
        return jsonify({"message": "User deleted successfully."}), 200


user_controller = UserController()
