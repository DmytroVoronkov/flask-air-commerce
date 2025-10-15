from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from models import Role
from services.till_service import (
    get_all_tills, check_open_till, open_till_for_cashier, 
    close_till_for_cashier, get_cashier_open_till,
    reopen_till_for_cashier
)
import logging

logger = logging.getLogger(__name__)
tills_bp = Blueprint('tills', __name__)

@tills_bp.route('/tills', methods=['GET'])
@jwt_required()
def tills():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} requested tills")

        tills_list, success, error_msg = get_all_tills(user_id, role)
        if success:
            return jsonify(tills_list)
        else:
            logger.error(f"Error retrieving tills: {error_msg}")
            return jsonify({'error': error_msg}), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving tills: {e}")
        return jsonify({'error': 'Failed to retrieve tills'}), 500

@tills_bp.route('/tills/open', methods=['GET'])
@jwt_required()
def check_open_till_route():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} checking open tills")

        open_till_data, is_open, error_msg = check_open_till()
        if error_msg:
            logger.error(f"Error checking open till: {error_msg}")
            return jsonify({'error': error_msg}), 500
        
        if is_open:
            return jsonify({
                'is_open': True,
                **open_till_data
            }), 200
        else:
            return jsonify({'is_open': False}), 200
            
    except Exception as e:
        logger.error(f"Unexpected error checking open till: {e}")
        return jsonify({'error': 'Failed to check open till'}), 500

@tills_bp.route('/tills/open', methods=['POST'])
@jwt_required()
def open_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to open a till")

        # Проверка роли
        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to open a till")
            return jsonify({'error': 'Only cashiers can open tills'}), 403

        # Используем сервис для открытия кассы
        till_data, success, error_msg = open_till_for_cashier(user_id)
        if success:
            return jsonify({
                'message': 'Till opened successfully',
                **till_data
            }), 201
        else:
            return jsonify({'error': error_msg}), 400
            
    except Exception as e:
        logger.error(f"Unexpected error opening till: {e}")
        return jsonify({'error': 'Failed to open till'}), 500

@tills_bp.route('/tills/close', methods=['POST'])
@jwt_required()
def close_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to close a till")

        # Проверка роли
        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to close a till")
            return jsonify({'error': 'Only cashiers can close tills'}), 403

        # Используем сервис для закрытия кассы
        till_data, success, error_msg = close_till_for_cashier(user_id)
        if success:
            return jsonify({
                'message': 'Till closed successfully',
                **till_data
            }), 200
        else:
            return jsonify({'error': error_msg}), 400
            
    except Exception as e:
        logger.error(f"Unexpected error closing till: {e}")
        return jsonify({'error': 'Failed to close till'}), 500

@tills_bp.route('/tills/<int:till_id>/reopen', methods=['POST'])
@jwt_required()
def reopen_till(till_id):
    try:
        claims = get_jwt()
        admin_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {admin_id} with role {role} attempting to reopen till {till_id}")

        # Проверка роли
        if role != Role.ADMIN.value:
            logger.warning(f"User {admin_id} with role {role} attempted to reopen till {till_id}")
            return jsonify({'error': 'Only admins can reopen tills'}), 403

        # Используем сервис для повторного открытия кассы
        till_data, success, error_msg = reopen_till_for_cashier(admin_id, till_id)
        if success:
            return jsonify({
                'message': 'Till reopened successfully',
                **till_data
            }), 200
        else:
            return jsonify({'error': error_msg}), 400
            
    except Exception as e:
        logger.error(f"Unexpected error reopening till {till_id}: {e}")
        return jsonify({'error': 'Failed to reopen till'}), 500