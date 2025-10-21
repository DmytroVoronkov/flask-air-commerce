from flask import Blueprint, redirect, url_for, flash, request
from flask_jwt_extended import jwt_required, get_jwt
from models import Role, ShiftStatus
from services.shift_service import open_shift as shift_service_open_shift, close_shift as shift_service_close_shift
import logging
logger = logging.getLogger(__name__)

shifts_bp = Blueprint('shifts', __name__)

@shifts_bp.route('/web/shifts/open', methods=['POST'])
@jwt_required()
def open_shift():
    claims = get_jwt()
    if claims['role'] != Role.CASHIER.value:
        flash('Тільки касири можуть відкривати зміни', 'error')
        return redirect(url_for('web.dashboard'))
    user_id = int(claims['sub'])
    cash_desk_id = request.form.get('cash_desk_id')
    if not cash_desk_id:
        flash('Виберіть касу', 'error')
        return redirect(url_for('web.dashboard'))
    shift_data, success, error_msg = shift_service_open_shift(user_id, int(cash_desk_id))
    if success:
        flash(f'Зміну успішно відкрито на касі {shift_data["cash_desk_name"]}!', 'success')
    else:
        flash(f'Помилка відкриття зміни: {error_msg}', 'error')
    return redirect(url_for('web.dashboard'))

@shifts_bp.route('/web/shifts/close', methods=['POST'])
@jwt_required()
def close_shift():
    claims = get_jwt()
    if claims['role'] != Role.CASHIER.value:
        flash('Тільки касири можуть закривати зміни', 'error')
        return redirect(url_for('web.dashboard'))
    user_id = int(claims['sub'])
    shift_data, success, error_msg = shift_service_close_shift(user_id)
    if success:
        flash('Зміну успішно закрито!', 'success')
    else:
        flash(f'Помилка закриття зміни: {error_msg}', 'error')
    return redirect(url_for('web.dashboard'))