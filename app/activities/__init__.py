# Activities module package
from flask import Blueprint

activities_bp = Blueprint('activities', __name__, template_folder='templates')

from app.activities import routes  # noqa: E402, F401
