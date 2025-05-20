# app/__init__.py
from flask import Flask
from app.dashboards.ameaca_geral_terras_indigenas import (
    register_ameaca_terra_indigena_dashboard,
)
from app.dashboards.ameaca_geral_area_de_protecao import register_area_de_protecao_dashboard
from app.dashboards.ameaca_ucs              import register_ucs_dashboard
from app.dashboards.pressao_area_de_protecao import (
    register_pressao_area_de_protecao_dashboard,
)
from app.dashboards.pressao_terras_indigenas import (
    register_pressao_terra_indigena_dashboard,
)
from app.dashboards.pressao_ucs import register_pressao_ucs_dashboard
def create_app():
    server = Flask(__name__)
    register_ameaca_terra_indigena_dashboard(server)  # /ameaca_terras_indigenas/
    register_area_de_protecao_dashboard(server) # /area_de_protecao/
    register_ucs_dashboard(server)              # /ucs/
    register_pressao_area_de_protecao_dashboard(server)  # /pressao_area_de_protecao/
    register_pressao_terra_indigena_dashboard(server)  # /pressao_terra_indigena/
    register_pressao_ucs_dashboard(server)   # /pressao_ucs/
    return server
