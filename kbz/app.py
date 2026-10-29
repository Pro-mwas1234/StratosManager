"""Application container: wires DB + all services once; every transport reuses it."""
from __future__ import annotations

from .core.db import Database, run_migrations
from .core.domain import TenantService, UserService
from .billing.entitlements import EntitlementService
from .services.invoicing import InvoicingService
from .services.retail import RetailService
from .services.restaurant import RestaurantService
from .services.hotel import HotelService
from .services.property import PropertyService
from .services.manufacturing import ManufacturingService
from .services.dashboard import DashboardService


class App:
    def __init__(self, db_path: str | None = None):
        self.db = Database(db_path)
        run_migrations(self.db)
        self.tenants = TenantService(self.db)
        self.users = UserService(self.db, self.tenants)
        self.entitlements = EntitlementService(self.db)
        self.invoicing = InvoicingService(self.db, self.entitlements)
        self.retail = RetailService(self.db, self.entitlements)
        self.restaurant = RestaurantService(self.db, self.entitlements, self.retail)
        self.hotel = HotelService(self.db, self.entitlements)
        self.property = PropertyService(self.db, self.entitlements)
        self.manufacturing = ManufacturingService(self.db, self.entitlements, self.retail)
        self.dashboard = DashboardService(self.db, self.entitlements, self.retail, self.hotel)
