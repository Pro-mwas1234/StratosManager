package ke.kazibiz.app.data.remote

import ke.kazibiz.app.data.remote.dto.*
import retrofit2.http.*

/**
 * Retrofit surface mirroring docs/API-CONTRACT.md v0.2 (frozen).
 * Money is always integer cents. All POSTs except /auth/register accept an
 * Idempotency-Key header (the offline outbox always sends one).
 */
interface KaziBizApi {

    // ---- auth ----
    @POST("auth/register")
    suspend fun register(@Body body: RegisterRequest): LoginResponse

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("auth/session")
    suspend fun session(): SessionResponse

    @POST("auth/logout")
    suspend fun logout()

    @GET("me")
    suspend fun me(): MeResponse

    @POST("auth/staff")
    suspend fun createStaff(@Body body: StaffRequest): Map<String, String>

    // ---- dashboard ----
    @GET("dashboard")
    suspend fun dashboard(): DashboardResponse

    // ---- retail (POS flagship) ----
    @GET("retail/products")
    suspend fun products(@Query("limit") limit: Int? = null): List<ProductDto>

    @GET("retail/products/{id}")
    suspend fun product(@Path("id") id: String): ProductDto

    @POST("retail/products")
    suspend fun createProduct(
        @Body body: CreateProductRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): ProductDto

    @POST("retail/products/{id}/stock")
    suspend fun adjustStock(
        @Path("id") id: String,
        @Body body: StockAdjustRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): StockAdjustResponse

    @GET("retail/stock/low")
    suspend fun lowStock(): List<ProductDto>

    @GET("retail/sales")
    suspend fun sales(@Query("limit") limit: Int? = null): List<SaleDto>

    @POST("retail/sales")
    suspend fun createSale(
        @Body body: CreateSaleRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): SaleDto

    @GET("retail/summary/today")
    suspend fun todaySummary(): TodaySummaryDto

    // ---- invoicing ----
    @GET("invoices/customers")
    suspend fun customers(): List<CustomerDto>

    @POST("invoices/customers")
    suspend fun createCustomer(
        @Body body: CreateCustomerRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): CustomerDto

    @GET("invoices/")
    suspend fun invoices(@Query("status") status: String? = null): List<InvoiceDto>

    @GET("invoices/{id}")
    suspend fun invoice(@Path("id") id: String): InvoiceDto

    @POST("invoices/")
    suspend fun createInvoice(
        @Body body: CreateInvoiceRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): InvoiceDto

    @POST("invoices/{id}/payments")
    suspend fun invoicePayment(
        @Path("id") id: String,
        @Body body: PaymentRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): InvoiceDto

    @POST("invoices/{id}/void")
    suspend fun voidInvoice(
        @Path("id") id: String,
        @Header("Idempotency-Key") key: String? = null,
    ): InvoiceDto

    @GET("invoices/reports/aging")
    suspend fun aging(): AgingReportDto

    // ---- restaurant ----
    @GET("restaurant/menu")
    suspend fun menu(): List<MenuItemDto>

    @POST("restaurant/menu")
    suspend fun createMenuItem(
        @Body body: CreateMenuItemRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): MenuItemDto

    @GET("restaurant/tables")
    suspend fun tables(): List<TableDto>

    @POST("restaurant/tables")
    suspend fun createTable(
        @Body body: CreateTableRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): TableDto

    @GET("restaurant/orders")
    suspend fun orders(@Query("status") status: String? = null): List<OrderDto>

    @POST("restaurant/orders")
    suspend fun createOrder(
        @Body body: CreateOrderRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): OrderDto

    @GET("restaurant/orders/{id}")
    suspend fun order(@Path("id") id: String): OrderDto

    @POST("restaurant/orders/{id}/items")
    suspend fun addOrderItem(
        @Path("id") id: String,
        @Body body: AddOrderItemRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): OrderDto

    @POST("restaurant/orders/{id}/close")
    suspend fun closeOrder(
        @Path("id") id: String,
        @Body body: CloseOrderRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): OrderDto

    @GET("restaurant/orders/{id}/kitchen-ticket")
    suspend fun kitchenTicket(@Path("id") id: String): TicketDto

    // ---- hotel ----
    @GET("hotel/rooms")
    suspend fun rooms(): List<RoomDto>

    @POST("hotel/rooms")
    suspend fun createRoom(
        @Body body: CreateRoomRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): RoomDto

    @GET("hotel/availability")
    suspend fun availability(
        @Query("check_in") checkIn: String,
        @Query("check_out") checkOut: String,
    ): List<RoomDto>

    @GET("hotel/bookings")
    suspend fun bookings(@Query("status") status: String? = null): List<BookingDto>

    @POST("hotel/bookings")
    suspend fun createBooking(
        @Body body: CreateBookingRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): BookingDto

    @POST("hotel/bookings/{id}/check-in")
    suspend fun checkIn(
        @Path("id") id: String,
        @Header("Idempotency-Key") key: String? = null,
    ): BookingDto

    @POST("hotel/bookings/{id}/check-out")
    suspend fun checkOut(
        @Path("id") id: String,
        @Header("Idempotency-Key") key: String? = null,
    ): BookingDto

    @POST("hotel/bookings/{id}/cancel")
    suspend fun cancelBooking(
        @Path("id") id: String,
        @Header("Idempotency-Key") key: String? = null,
    ): BookingDto

    @GET("hotel/reports/occupancy")
    suspend fun occupancy(@Query("date") date: String? = null): OccupancyDto

    // ---- property ----
    @GET("property/properties")
    suspend fun properties(): List<PropertyDto>

    @POST("property/properties")
    suspend fun createProperty(
        @Body body: CreatePropertyRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): PropertyDto

    @POST("property/units")
    suspend fun createUnit(
        @Body body: CreateUnitRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): UnitDto

    @GET("property/leases")
    suspend fun leases(@Query("status") status: String? = null): List<LeaseDto>

    @POST("property/leases")
    suspend fun createLease(
        @Body body: CreateLeaseRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): LeaseDto

    @POST("property/leases/{id}/end")
    suspend fun endLease(
        @Path("id") id: String,
        @Header("Idempotency-Key") key: String? = null,
    ): LeaseDto

    @POST("property/rent-bills")
    suspend fun createRentBill(
        @Body body: CreateRentBillRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): RentBillDto

    @GET("property/rent-bills/{id}")
    suspend fun rentBill(@Path("id") id: String): RentBillDto

    @POST("property/rent-bills/{id}/payments")
    suspend fun rentPayment(
        @Path("id") id: String,
        @Body body: PaymentRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): RentBillDto

    @GET("property/reports/arrears")
    suspend fun arrears(): ArrearsDto

    // ---- manufacturing ----
    @GET("manufacturing/boms")
    suspend fun boms(): List<BomDto>

    @POST("manufacturing/boms")
    suspend fun createBom(
        @Body body: CreateBomRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): BomDto

    @GET("manufacturing/boms/{id}")
    suspend fun bom(@Path("id") id: String): BomDto

    @GET("manufacturing/boms/{id}/explode")
    suspend fun explodeBom(@Path("id") id: String, @Query("qty") qty: Int): ExplodeDto

    @GET("manufacturing/work-orders")
    suspend fun workOrders(@Query("status") status: String? = null): List<WorkOrderDto>

    @POST("manufacturing/work-orders")
    suspend fun createWorkOrder(
        @Body body: CreateWorkOrderRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): WorkOrderDto

    @POST("manufacturing/work-orders/{id}/start")
    suspend fun startWorkOrder(
        @Path("id") id: String,
        @Header("Idempotency-Key") key: String? = null,
    ): WorkOrderDto

    @POST("manufacturing/work-orders/{id}/complete")
    suspend fun completeWorkOrder(
        @Path("id") id: String,
        @Body body: CompleteWorkOrderRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): WorkOrderDto

    // ---- billing ----
    @GET("billing/plans")
    suspend fun plans(): List<PlanDto>

    @GET("billing/usage")
    suspend fun usage(): UsageDto

    @POST("billing/subscribe")
    suspend fun subscribe(
        @Body body: SubscribeRequest,
        @Header("Idempotency-Key") key: String? = null,
    ): MeResponse
}
