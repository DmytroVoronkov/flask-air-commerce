from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models import Till, Role
from datetime import datetime
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

        if role == 'cashier':
            tills = Till.query.filter_by(cashier_id=user_id).all()
        else:
            tills = Till.query.all()

        tills_list = [
            {
                'id': till.id,
                'cashier_id': till.cashier_id,
                'cashier_name': till.cashier.name,
                'cashier_email': till.cashier.email,
                'opened_at': till.opened_at.isoformat(),
                'closed_at': till.closed_at.isoformat() if till.closed_at else None,
                'is_active': till.is_active,
                'total_amount': str(till.total_amount)
            } for till in tills
        ]
        logger.info(f"Retrieved {len(tills_list)} tills for user {user_id}")
        return jsonify(tills_list)
    except Exception as e:
        logger.error(f"Error retrieving tills: {e}")
        return jsonify({'error': 'Failed to retrieve tills'}), 500

@tills_bp.route('/tills/open', methods=['GET'])
@jwt_required()
def check_open_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} checking open tills")

        open_till = Till.query.filter_by(is_active=True).first()
        if open_till:
            return jsonify({
                'is_open': True,
                'till_id': open_till.id,
                'cashier_id': open_till.cashier_id,
                'cashier_name': open_till.cashier.name,
                'cashier_email': open_till.cashier.email,
                'opened_at': open_till.opened_at.isoformat(),
                'total_amount': str(open_till.total_amount)
            }), 200
        return jsonify({'is_open': False}), 200
    except Exception as e:
        logger.error(f"Error checking open till: {e}")
        return jsonify({'error': 'Failed to check open till'}), 500

@tills_bp.route('/tills/open', methods=['POST'])
@jwt_required()
def open_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to open a till")

        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to open a till")
            return jsonify({'error': 'Only cashiers can open tills'}), 403

        if Till.query.filter_by(is_active=True).count() > 0:
            logger.warning(f"User {user_id} attempted to open a till while another is active")
            return jsonify({'error': 'Another till is already open'}), 400

        new_till = Till(
            cashier_id=user_id,
            opened_at=datetime.now(),
            is_active=True,
            total_amount=0.0
        )
        Till.query.session.add(new_till)
        Till.query.session.commit()
        logger.info(f"User {user_id} opened till {new_till.id}")

        return jsonify({
            'message': 'Till opened successfully',
            'till_id': new_till.id,
            'cashier_id': new_till.cashier_id,
            'opened_at': new_till.opened_at.isoformat(),
            'total_amount': str(new_till.total_amount)
        }), 201

    except Exception as e:
        Till.query.session.rollback()
        logger.error(f"Error opening till for user {user_id}: {e}")
        return jsonify({'error': 'Failed to open till'}), 500

@tills_bp.route('/tills/close', methods=['POST'])
@jwt_required()
def close_till():
    try:
        claims = get_jwt()
        user_id = int(claims['sub'])
        role = claims['role']
        logger.info(f"User {user_id} with role {role} attempting to close a till")

        if role != Role.CASHIER.value:
            logger.warning(f"User {user_id} with role {role} attempted to close a till")
            return jsonify({'error': 'Only cashiers can close tills'}), 403

        open_till = Till.query.filter_by(cashier_id=user_id, is_active=True).first()
        if not open_till:
            logger.warning(f"No open till found for user {user_id}")
            return jsonify({'error': 'No open till found for this cashier'}), 404

        open_till.is_active = False
        open_till.closed_at = datetime.now()
        Till.query.session.commit()
        logger.info(f"User {user_id} closed till {open_till.id}")

        return jsonify({
            'message': 'Till closed successfully',
            'till_id': open_till.id,
            'closed_at': open_till.closed_at.isoformat()
        }), 200

    except Exception as e:
        Till.query.session.rollback()
        logger.error(f"Error closing till for user {user_id}: {e}")
        return jsonify({'error': 'Failed to close till'}), 500