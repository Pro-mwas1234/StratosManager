package ke.stratosmanager.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// AUTO-MIRRORED FROM docs/API-CONTRACT.md v0.2 — keep in lockstep with kbz/api/schemas.py.
// Money is always integer cents. Nullable fields cover JSON-nulls and absent dashboard sections.

@Serializable
data class RegisterRequest(
    @SerialName("email") val email: String,
    @SerialName("password") val password: String,
    @SerialName("tenant_name") val tenantName: String,
    @SerialName("kra_pin") val kraPin: String? = null,
    @SerialName("phone") val phone: String? = null,
    @SerialName("plan_id") val planId: String? = null
)

@Serializable
data class LoginRequest(
    @SerialName("email") val email: String,
    @SerialName("password") val password: String
)

@Serializable
data class StaffRequest(
    @SerialName("email") val email: String,
    @SerialName("password") val password: String
)

@Serializable
data class UserDto(
    @SerialName("id") val id: String,
    @SerialName("email") val email: String,
    @SerialName("role") val role: String,
    @SerialName("tenant_id") val tenantId: String? = null
)

@Serializable
data class LoginResponse(
    @SerialName("token") val token: String,
    @SerialName("user_id") val userId: String,
    @SerialName("email") val email: String,
    @SerialName("role") val role: String,
    @SerialName("tenant_id") val tenantId: String,
    @SerialName("tenant_name") val tenantName: String,
    @SerialName("plan") val plan: String,
    @SerialName("plan_name") val planName: String,
    @SerialName("features") val features: List<String> = emptyList()
)

@Serializable
data class SessionResponse(
    @SerialName("valid") val valid: Boolean,
    @SerialName("user_id") val userId: String,
    @SerialName("email") val email: String,
    @SerialName("role") val role: String,
    @SerialName("tenant_id") val tenantId: String,
    @SerialName("tenant_name") val tenantName: String,
    @SerialName("plan") val plan: String
)

@Serializable
data class TenantDto(
    @SerialName("id") val id: String,
    @SerialName("name") val name: String,
    @SerialName("kra_pin") val kraPin: String? = null,
    @SerialName("phone") val phone: String? = null
)

@Serializable
data class PlanDto(
    @SerialName("id") val id: String? = null,
    @SerialName("name") val name: String,
    @SerialName("features") val features: List<String> = emptyList(),
    @SerialName("price_kes_cents") val priceKesCents: Long? = null,
    @SerialName("limits") val limits: Map<String,Long>? = null
)

@Serializable
data class MeResponse(
    @SerialName("user") val user: UserDto,
    @SerialName("tenant") val tenant: TenantDto,
    @SerialName("plan") val plan: PlanDto
)

@Serializable
data class DashboardTenantDto(
    @SerialName("plan_id") val planId: String,
    @SerialName("plan_name") val planName: String,
    @SerialName("features") val features: List<String> = emptyList()
)

@Serializable
data class RetailDashDto(
    @SerialName("today_sales_count") val todaySalesCount: Int,
    @SerialName("today_total_cents") val todayTotalCents: Long,
    @SerialName("today_total_fmt") val todayTotalFmt: String,
    @SerialName("low_stock_count") val lowStockCount: Int
)

@Serializable
data class InvoicingDashDto(
    @SerialName("open_invoices") val openInvoices: Int,
    @SerialName("receivable_cents") val receivableCents: Long,
    @SerialName("receivable_fmt") val receivableFmt: String
)

@Serializable
data class RestaurantDashDto(
    @SerialName("open_orders") val openOrders: Int
)

@Serializable
data class HotelDashDto(
    @SerialName("arrivals_today") val arrivalsToday: Int,
    @SerialName("departures_today") val departuresToday: Int,
    @SerialName("in_house") val inHouse: Int,
    @SerialName("occupancy_pct") val occupancyPct: Double
)

@Serializable
data class PropertyDashDto(
    @SerialName("unpaid_bills") val unpaidBills: Int,
    @SerialName("arrears_cents") val arrearsCents: Long,
    @SerialName("arrears_fmt") val arrearsFmt: String
)

@Serializable
data class ManufacturingDashDto(
    @SerialName("work_orders_open") val workOrdersOpen: Int
)

@Serializable
data class DashboardResponse(
    @SerialName("generated_at") val generatedAt: String,
    @SerialName("tenant") val tenant: DashboardTenantDto,
    @SerialName("usage") val usage: UsageDto,
    @SerialName("retail") val retail: RetailDashDto? = null,
    @SerialName("invoicing") val invoicing: InvoicingDashDto? = null,
    @SerialName("restaurant") val restaurant: RestaurantDashDto? = null,
    @SerialName("hotel") val hotel: HotelDashDto? = null,
    @SerialName("property") val property: PropertyDashDto? = null,
    @SerialName("manufacturing") val manufacturing: ManufacturingDashDto? = null
)

@Serializable
data class ProductDto(
    @SerialName("id") val id: String,
    @SerialName("sku") val sku: String,
    @SerialName("name") val name: String,
    @SerialName("category") val category: String? = null,
    @SerialName("sale_price_cents") val salePriceCents: Long,
    @SerialName("cost_price_cents") val costPriceCents: Long,
    @SerialName("vat_exempt") val vatExempt: Int,
    @SerialName("reorder_level") val reorderLevel: Int,
    @SerialName("active") val active: Int,
    @SerialName("stock_qty") val stockQty: Long
)

@Serializable
data class CreateProductRequest(
    @SerialName("sku") val sku: String,
    @SerialName("name") val name: String,
    @SerialName("sale_price_cents") val salePriceCents: Long,
    @SerialName("cost_price_cents") val costPriceCents: Long? = null,
    @SerialName("category") val category: String? = null,
    @SerialName("vat_exempt") val vatExempt: Boolean? = null,
    @SerialName("reorder_level") val reorderLevel: Int? = null
)

@Serializable
data class StockAdjustRequest(
    @SerialName("delta") val delta: Int,
    @SerialName("reason") val reason: String? = null,
    @SerialName("ref") val ref: String? = null
)

@Serializable
data class StockAdjustResponse(
    @SerialName("movement_id") val movementId: String,
    @SerialName("product_id") val productId: String,
    @SerialName("delta") val delta: Int,
    @SerialName("on_hand") val onHand: Long
)

@Serializable
data class LowStockRowDto(
    @SerialName("sku") val sku: String,
    @SerialName("name") val name: String,
    @SerialName("on_hand") val onHand: Long,
    @SerialName("reorder_level") val reorderLevel: Long
)

@Serializable
data class SaleItemDto(
    @SerialName("id") val id: String,
    @SerialName("product_id") val productId: String,
    @SerialName("qty") val qty: Int,
    @SerialName("unit_price_cents") val unitPriceCents: Long,
    @SerialName("line_total_cents") val lineTotalCents: Long
)

@Serializable
data class SaleDto(
    @SerialName("id") val id: String,
    @SerialName("receipt_no") val receiptNo: String,
    @SerialName("total_cents") val totalCents: Long,
    @SerialName("payment_method") val paymentMethod: String,
    @SerialName("mpesa_ref") val mpesaRef: String? = null,
    @SerialName("cashier") val cashier: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("total_fmt") val totalFmt: String? = null,
    @SerialName("items") val items: List<SaleItemDto>? = null
)

@Serializable
data class SaleLineInput(
    @SerialName("product_id") val productId: String,
    @SerialName("qty") val qty: Int
)

@Serializable
data class CreateSaleRequest(
    @SerialName("items") val items: List<SaleLineInput> = emptyList(),
    @SerialName("payment_method") val paymentMethod: String,
    @SerialName("mpesa_ref") val mpesaRef: String? = null,
    @SerialName("cashier") val cashier: String? = null
)

@Serializable
data class TodaySummaryDto(
    @SerialName("date") val date: String,
    @SerialName("sales_count") val salesCount: Int,
    @SerialName("total_cents") val totalCents: Long,
    @SerialName("total_fmt") val totalFmt: String
)

@Serializable
data class CustomerDto(
    @SerialName("id") val id: String,
    @SerialName("name") val name: String,
    @SerialName("email") val email: String? = null,
    @SerialName("phone") val phone: String? = null,
    @SerialName("kra_pin") val kraPin: String? = null,
    @SerialName("address") val address: String? = null
)

@Serializable
data class CreateCustomerRequest(
    @SerialName("name") val name: String,
    @SerialName("email") val email: String? = null,
    @SerialName("phone") val phone: String? = null,
    @SerialName("kra_pin") val kraPin: String? = null,
    @SerialName("address") val address: String? = null
)

@Serializable
data class InvoiceLineDto(
    @SerialName("id") val id: String,
    @SerialName("description") val description: String,
    @SerialName("qty") val qty: Double,
    @SerialName("unit_price_cents") val unitPriceCents: Long,
    @SerialName("vat_rate") val vatRate: Double,
    @SerialName("net_cents") val netCents: Long,
    @SerialName("vat_cents") val vatCents: Long
)

@Serializable
data class PaymentDto(
    @SerialName("id") val id: String,
    @SerialName("method") val method: String,
    @SerialName("reference") val reference: String? = null,
    @SerialName("amount_cents") val amountCents: Long,
    @SerialName("paid_at") val paidAt: String? = null
)

@Serializable
data class InvoiceDto(
    @SerialName("id") val id: String,
    @SerialName("number") val number: String,
    @SerialName("customer_id") val customerId: String? = null,
    @SerialName("status") val status: String,
    @SerialName("issue_date") val issueDate: String,
    @SerialName("due_date") val dueDate: String? = null,
    @SerialName("notes") val notes: String? = null,
    @SerialName("net_cents") val netCents: Long,
    @SerialName("vat_cents") val vatCents: Long,
    @SerialName("gross_cents") val grossCents: Long,
    @SerialName("paid_cents") val paidCents: Long,
    @SerialName("balance_cents") val balanceCents: Long? = null,
    @SerialName("gross_fmt") val grossFmt: String? = null,
    @SerialName("lines") val lines: List<InvoiceLineDto>? = null,
    @SerialName("payments") val payments: List<PaymentDto>? = null
)

@Serializable
data class InvoiceLineInput(
    @SerialName("description") val description: String,
    @SerialName("qty") val qty: Double,
    @SerialName("unit_price_cents") val unitPriceCents: Long,
    @SerialName("vat_rate") val vatRate: Double
)

@Serializable
data class CreateInvoiceRequest(
    @SerialName("customer_id") val customerId: String? = null,
    @SerialName("lines") val lines: List<InvoiceLineInput> = emptyList(),
    @SerialName("due_date") val dueDate: String? = null,
    @SerialName("notes") val notes: String? = null,
    @SerialName("inclusive_vat") val inclusiveVat: Boolean? = null
)

@Serializable
data class PaymentRequest(
    @SerialName("amount_cents") val amountCents: Long,
    @SerialName("method") val method: String,
    @SerialName("reference") val reference: String? = null
)

@Serializable
data class AgingReportDto(
    @SerialName("as_of") val asOf: String,
    @SerialName("open_invoices") val openInvoices: Int,
    @SerialName("buckets_cents") val bucketsCents: Map<String,Long> = emptyMap(),
    @SerialName("buckets_kes") val bucketsKes: Map<String,String> = emptyMap()
)

@Serializable
data class MenuItemDto(
    @SerialName("id") val id: String,
    @SerialName("name") val name: String,
    @SerialName("category") val category: String? = null,
    @SerialName("price_cents") val priceCents: Long,
    @SerialName("available") val available: Int,
    @SerialName("product_id") val productId: String? = null
)

@Serializable
data class CreateMenuItemRequest(
    @SerialName("name") val name: String,
    @SerialName("price_cents") val priceCents: Long,
    @SerialName("category") val category: String? = null,
    @SerialName("product_id") val productId: String? = null
)

@Serializable
data class TableDto(
    @SerialName("id") val id: String,
    @SerialName("label") val label: String,
    @SerialName("seats") val seats: Int,
    @SerialName("status") val status: String
)

@Serializable
data class CreateTableRequest(
    @SerialName("label") val label: String,
    @SerialName("seats") val seats: Int
)

@Serializable
data class OrderItemDto(
    @SerialName("id") val id: String,
    @SerialName("menu_item_id") val menuItemId: String,
    @SerialName("qty") val qty: Int,
    @SerialName("unit_price_cents") val unitPriceCents: Long,
    @SerialName("line_total_cents") val lineTotalCents: Long,
    @SerialName("notes") val notes: String? = null
)

@Serializable
data class OrderDto(
    @SerialName("id") val id: String,
    @SerialName("ticket_no") val ticketNo: String,
    @SerialName("table_id") val tableId: String? = null,
    @SerialName("status") val status: String,
    @SerialName("total_cents") val totalCents: Long,
    @SerialName("service_charge_cents") val serviceChargeCents: Long,
    @SerialName("grand_total_cents") val grandTotalCents: Long? = null,
    @SerialName("grand_total_fmt") val grandTotalFmt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("items") val items: List<OrderItemDto>? = null
)

@Serializable
data class CreateOrderRequest(
    @SerialName("table_id") val tableId: String? = null
)

@Serializable
data class AddOrderItemRequest(
    @SerialName("menu_item_id") val menuItemId: String,
    @SerialName("qty") val qty: Int,
    @SerialName("notes") val notes: String? = null
)

@Serializable
data class CloseOrderRequest(
    @SerialName("payment_method") val paymentMethod: String
)

@Serializable
data class TicketDto(
    @SerialName("ticket") val ticket: String
)

@Serializable
data class RoomDto(
    @SerialName("id") val id: String,
    @SerialName("number") val number: String,
    @SerialName("room_type") val roomType: String,
    @SerialName("rate_cents") val rateCents: Long,
    @SerialName("status") val status: String
)

@Serializable
data class CreateRoomRequest(
    @SerialName("number") val number: String,
    @SerialName("rate_cents") val rateCents: Long,
    @SerialName("room_type") val roomType: String
)

@Serializable
data class AvailabilityDto(
    @SerialName("room") val room: String,
    @SerialName("type") val type: String,
    @SerialName("rate_cents") val rateCents: Long,
    @SerialName("free") val free: Boolean
)

@Serializable
data class BookingDto(
    @SerialName("id") val id: String,
    @SerialName("guest_name") val guestName: String,
    @SerialName("guest_phone") val guestPhone: String? = null,
    @SerialName("room_id") val roomId: String,
    @SerialName("check_in_date") val checkInDate: String,
    @SerialName("check_out_date") val checkOutDate: String,
    @SerialName("status") val status: String,
    @SerialName("nights") val nights: Int,
    @SerialName("total_cents") val totalCents: Long,
    @SerialName("total_fmt") val totalFmt: String? = null
)

@Serializable
data class CreateBookingRequest(
    @SerialName("guest_name") val guestName: String,
    @SerialName("guest_phone") val guestPhone: String? = null,
    @SerialName("room_id") val roomId: String,
    @SerialName("check_in") val checkIn: String,
    @SerialName("check_out") val checkOut: String
)

@Serializable
data class OccupancyDto(
    @SerialName("date") val date: String,
    @SerialName("rooms_total") val roomsTotal: Int,
    @SerialName("rooms_occupied") val roomsOccupied: Int,
    @SerialName("occupancy_pct") val occupancyPct: Double
)

@Serializable
data class PropertyDto(
    @SerialName("id") val id: String,
    @SerialName("name") val name: String,
    @SerialName("location") val location: String? = null
)

@Serializable
data class CreatePropertyRequest(
    @SerialName("name") val name: String,
    @SerialName("location") val location: String? = null
)

@Serializable
data class UnitDto(
    @SerialName("id") val id: String,
    @SerialName("property_id") val propertyId: String,
    @SerialName("label") val label: String,
    @SerialName("rent_cents") val rentCents: Long,
    @SerialName("status") val status: String
)

@Serializable
data class CreateUnitRequest(
    @SerialName("property_id") val propertyId: String,
    @SerialName("label") val label: String,
    @SerialName("rent_cents") val rentCents: Long
)

@Serializable
data class LeaseDto(
    @SerialName("id") val id: String,
    @SerialName("unit_id") val unitId: String,
    @SerialName("tenant_name") val tenantName: String,
    @SerialName("tenant_phone") val tenantPhone: String? = null,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String,
    @SerialName("rent_cents") val rentCents: Long,
    @SerialName("deposit_cents") val depositCents: Long,
    @SerialName("status") val status: String
)

@Serializable
data class CreateLeaseRequest(
    @SerialName("unit_id") val unitId: String,
    @SerialName("tenant_name") val tenantName: String,
    @SerialName("tenant_phone") val tenantPhone: String? = null,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String,
    @SerialName("rent_cents") val rentCents: Long? = null,
    @SerialName("deposit_cents") val depositCents: Long? = null
)

@Serializable
data class RentBillDto(
    @SerialName("id") val id: String,
    @SerialName("lease_id") val leaseId: String,
    @SerialName("period") val period: String,
    @SerialName("due_date") val dueDate: String,
    @SerialName("amount_cents") val amountCents: Long,
    @SerialName("paid_cents") val paidCents: Long,
    @SerialName("status") val status: String,
    @SerialName("balance_cents") val balanceCents: Long? = null,
    @SerialName("tenant_name") val tenantName: String? = null,
    @SerialName("balance_fmt") val balanceFmt: String? = null
)

@Serializable
data class CreateRentBillRequest(
    @SerialName("lease_id") val leaseId: String,
    @SerialName("period") val period: String? = null,
    @SerialName("due_day") val dueDay: Int? = null
)

@Serializable
data class ArrearsRowDto(
    @SerialName("bill_id") val billId: String,
    @SerialName("tenant_name") val tenantName: String,
    @SerialName("period") val period: String,
    @SerialName("due_date") val dueDate: String,
    @SerialName("balance_cents") val balanceCents: Long,
    @SerialName("overdue_days") val overdueDays: Int,
    @SerialName("balance_fmt") val balanceFmt: String? = null
)

@Serializable
data class ArrearsDto(
    @SerialName("as_of") val asOf: String,
    @SerialName("total_arrears_cents") val totalArrearsCents: Long,
    @SerialName("total_arrears_fmt") val totalArrearsFmt: String,
    @SerialName("bills") val bills: List<ArrearsRowDto> = emptyList()
)

@Serializable
data class BomDto(
    @SerialName("id") val id: String,
    @SerialName("product_id") val productId: String,
    @SerialName("version") val version: String,
    @SerialName("components") val components: List<BomComponentDto>? = null
)

@Serializable
data class BomComponentDto(
    @SerialName("product_id") val productId: String,
    @SerialName("sku") val sku: String,
    @SerialName("name") val name: String,
    @SerialName("qty_per_unit") val qtyPerUnit: Double,
    @SerialName("on_hand") val onHand: Double
)

@Serializable
data class BomComponentInput(
    @SerialName("product_id") val productId: String,
    @SerialName("qty") val qty: Double
)

@Serializable
data class CreateBomRequest(
    @SerialName("product_id") val productId: String,
    @SerialName("components") val components: List<BomComponentInput> = emptyList(),
    @SerialName("version") val version: String? = null
)

@Serializable
data class ExplodeRowDto(
    @SerialName("sku") val sku: String,
    @SerialName("name") val name: String,
    @SerialName("required") val required: Double,
    @SerialName("on_hand") val onHand: Double,
    @SerialName("shortfall") val shortfall: Double
)

@Serializable
data class WorkOrderDto(
    @SerialName("id") val id: String,
    @SerialName("bom_id") val bomId: String,
    @SerialName("wo_no") val woNo: String? = null,
    @SerialName("qty_planned") val qtyPlanned: Double,
    @SerialName("qty_produced") val qtyProduced: Double,
    @SerialName("status") val status: String,
    @SerialName("notes") val notes: String? = null,
    @SerialName("created_at") val createdAt: String? = null
)

@Serializable
data class CreateWorkOrderRequest(
    @SerialName("bom_id") val bomId: String,
    @SerialName("qty_planned") val qtyPlanned: Double,
    @SerialName("notes") val notes: String? = null
)

@Serializable
data class CompleteWorkOrderRequest(
    @SerialName("qty_produced") val qtyProduced: Double
)

@Serializable
data class MeterDto(
    @SerialName("used") val used: Long,
    @SerialName("limit") val limit: Long? = null
)

@Serializable
data class UsageDto(
    @SerialName("tenant") val tenant: String,
    @SerialName("plan") val plan: String,
    @SerialName("price_kes_cents") val priceKesCents: Long,
    @SerialName("month") val month: String,
    @SerialName("usage") val usage: Map<String,MeterDto> = emptyMap()
)

@Serializable
data class SubscribeRequest(
    @SerialName("plan_id") val planId: String
)
