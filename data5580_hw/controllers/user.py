import logging

from flask import jsonify, request

from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from data5580_hw.services.database.database_client import db
from data5580_hw.services.database.user_model import UserSQL
from data5580_hw.models.user import User

logger = logging.getLogger(__name__)


class UserController:
    @staticmethod
    def create_user():
        try:
            user = User.model_validate(request.get_json(force=True))
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        user_sql = UserSQL(name=user.name, email=user.email, id=user.id)
        db.session.add(user_sql)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"error": "User already exists"}), 400

        logging.info(f"user created, {user.id} for {user.email}")
        return jsonify(user.model_dump()), 200


    @staticmethod
    def get_user_by_id(user_id: str) -> tuple[str, int]:
        logger.debug(f'Got user_id {user_id}')

        user_sql = db.session.query(UserSQL).filter_by(UserSQL.id==user_id).first()
        
        user= User.model_validate(user_sql, from_attribute=True)

        if not user:
            return jsonify({}), 404
        
        logging.info(f"User created, {user_id} for {user.email}.")

        return user.model_dump_json(), 200

    @staticmethod
    def update_user(user_id: str) -> tuple[str, int]:

        user = User.model_validate(request.get_json(force=True))

        user_sql = db.session.query(UserSQL).filter(UserSQL.id == user_id).first()

        user_sql.name = user.name
        user_sql.email = user.email

        db.session.commit()

        return user.model_dump_json(), 200

user_controller = UserController()

#triggering sonar scan