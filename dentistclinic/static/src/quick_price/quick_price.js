/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { PERMANENT, PRIMARY, toothInfo } from "../odontogram/odontogram_field";

/**
 * Hızlı Fiyat — a till-like quote screen.
 *
 * Teeth are selected on a mini chart; tapping a procedure tile adds one line
 * per selected tooth (or one line for procedures that are not per tooth).
 * The ticket is priced in the chosen currency (fixed tourist prices or the
 * converted TRY price), checked against the user's discount limit, then
 * turned into a treatment plan, booked into a free slot and shared
 * (WhatsApp text, PDF, or a full-screen presentation for the patient).
 */

let lineSeq = 0;

function toUtcString(date) {
    return date.toISOString().slice(0, 10);
}

export class QuickPrice extends Component {
    static template = "dentistclinic.QuickPrice";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.searchRef = useRef("search");
        this.state = useState({
            loading: true,
            setup: null,
            catalog: { categories: [], procedures: [], currency: null },
            currencyId: null,
            category: "all",
            query: "",
            dentition: "permanent",
            selected: [],
            lines: [],
            globalDiscount: 0,
            patient: null,
            patientQuery: "",
            patientResults: [],
            newPatient: null,
            plan: null,
            step: "quote", // quote | book | done
            doctorId: null,
            day: toUtcString(new Date(Date.now() + 86400000)),
            slots: [],
            slotsLoading: false,
            booking: null,
            presenting: false,
            busy: false,
        });
        this.onKeydown = (ev) => this._onKeydown(ev);

        onWillStart(async () => {
            const setup = await this.orm.call("dental.quick.price", "get_setup", []);
            this.state.setup = setup;
            const companyCurrency = setup.currencies.find((c) => c.name === setup.company_currency) || setup.currencies[0];
            this.state.currencyId = companyCurrency?.id;
            this.state.doctorId = setup.doctors[0]?.id || null;
            await this.loadCatalog();
            const patientId = this.props.action?.params?.patient_id || this.props.action?.context?.default_patient_id;
            if (patientId) {
                this.state.patient = await this.orm.call("dental.quick.price", "get_patient", [patientId]);
            }
            this.state.loading = false;
        });
        onMounted(() => document.addEventListener("keydown", this.onKeydown));
        onWillUnmount(() => document.removeEventListener("keydown", this.onKeydown));
    }

    // ------------------------------------------------------------------
    // Catalogue / currency
    // ------------------------------------------------------------------

    async loadCatalog() {
        this.state.catalog = await this.orm.call("dental.quick.price", "get_catalog", [this.state.currencyId]);
        // Reprice the ticket in the new currency.
        const prices = new Map(this.state.catalog.procedures.map((p) => [p.id, p]));
        for (const line of this.state.lines) {
            const procedure = prices.get(line.procedureId);
            if (procedure) {
                line.price = procedure.price;
                line.converted = procedure.converted;
            }
        }
    }

    async setCurrency(id) {
        if (id === this.state.currencyId || this.state.plan) {
            return;
        }
        this.state.currencyId = id;
        await this.loadCatalog();
    }

    get currency() {
        return this.state.catalog.currency || { name: "TRY", decimals: 2 };
    }

    money(amount) {
        try {
            return new Intl.NumberFormat(document.documentElement.lang || "tr-TR", {
                style: "currency",
                currency: this.currency.name,
                minimumFractionDigits: this.currency.decimals,
                maximumFractionDigits: this.currency.decimals,
            }).format(amount || 0);
        } catch {
            return `${(amount || 0).toFixed(2)} ${this.currency.name}`;
        }
    }

    get selectedDentition() {
        const kinds = new Set(this.state.selected.map((n) => (Math.floor(n / 10) >= 5 ? "primary" : "permanent")));
        return kinds.size === 1 ? [...kinds][0] : kinds.size ? "mixed" : null;
    }

    get visibleProcedures() {
        const q = this.state.query.trim().toLocaleLowerCase("tr");
        return this.state.catalog.procedures.filter((p) =>
            (this.state.category === "all" || p.category_id === this.state.category)
            && (!q || p.name.toLocaleLowerCase("tr").includes(q)));
    }

    procedureAllowed(procedure) {
        const kind = this.selectedDentition;
        if (!kind || procedure.dentition === "all") {
            return true;
        }
        return kind !== "mixed" && procedure.dentition === kind;
    }

    // ------------------------------------------------------------------
    // Mini chart
    // ------------------------------------------------------------------

    get arches() {
        return this.state.dentition === "primary" ? PRIMARY : PERMANENT;
    }

    tooth(number) {
        return toothInfo(number);
    }

    toothClass(number) {
        const used = this.state.lines.some((l) => l.tooth === String(number));
        return [
            "o_qp_tooth",
            this.state.selected.includes(number) ? "is-selected" : "",
            used ? "is-used" : "",
        ].join(" ");
    }

    toggleTooth(number) {
        if (this.state.plan) {
            return;
        }
        const index = this.state.selected.indexOf(number);
        if (index >= 0) {
            this.state.selected.splice(index, 1);
        } else {
            this.state.selected.push(number);
        }
    }

    setDentition(value) {
        this.state.dentition = value;
        this.state.selected = [];
    }

    clearSelection() {
        this.state.selected = [];
    }

    // ------------------------------------------------------------------
    // Ticket
    // ------------------------------------------------------------------

    addProcedure(procedure) {
        if (this.state.plan) {
            this.notification.add("Bu teklif plana aktarıldı. Değişiklik için yeni teklif başlatın.", { type: "warning" });
            return;
        }
        if (!this.procedureAllowed(procedure)) {
            this.notification.add(
                procedure.dentition === "primary" ? "Bu işlem süt dişleri içindir." : "Bu işlem daimi dişler içindir.",
                { type: "warning" });
            return;
        }
        const teeth = procedure.per_tooth ? [...this.state.selected].sort((a, b) => a - b) : [];
        if (procedure.per_tooth && !teeth.length) {
            this.notification.add(`"${procedure.name}" diş bazında uygulanır: önce şemadan diş seçin.`, { type: "info" });
            return;
        }
        for (const tooth of teeth.length ? teeth : [null]) {
            this.state.lines.push({
                key: ++lineSeq,
                procedureId: procedure.id,
                name: procedure.name,
                tooth: tooth ? String(tooth) : "",
                price: procedure.price,
                converted: procedure.converted,
                discount: 0,
                duration: procedure.duration || 0.5,
            });
        }
        if (procedure.per_tooth) {
            this.state.selected = [];
        }
    }

    removeLine(key) {
        if (this.state.plan) {
            return;
        }
        const index = this.state.lines.findIndex((l) => l.key === key);
        if (index >= 0) {
            this.state.lines.splice(index, 1);
        }
    }

    setLineDiscount(line, value) {
        line.discount = Math.min(Math.max(parseFloat(value) || 0, 0), 100);
    }

    setGlobalDiscount(value) {
        this.state.globalDiscount = Math.min(Math.max(parseFloat(value) || 0, 0), 100);
    }

    isPrimaryTooth(tooth) {
        return parseInt(tooth, 10) >= 50;
    }

    lineTotal(line) {
        return line.price * (1 - line.discount / 100);
    }

    get subtotal() {
        return this.state.lines.reduce((sum, line) => sum + this.lineTotal(line), 0);
    }

    get globalDiscountAmount() {
        return this.subtotal * this.state.globalDiscount / 100;
    }

    get total() {
        return this.subtotal - this.globalDiscountAmount;
    }

    get totalDuration() {
        return this.state.lines.reduce((sum, line) => sum + (line.duration || 0), 0);
    }

    get durationLabel() {
        const minutes = Math.round(this.totalDuration * 60);
        return minutes >= 60 ? `${Math.floor(minutes / 60)} sa ${minutes % 60 ? `${minutes % 60} dk` : ""}`.trim() : `${minutes} dk`;
    }

    get maxDiscount() {
        return this.state.setup?.max_discount ?? 0;
    }

    get discountError() {
        const limit = this.maxDiscount;
        if ([this.state.globalDiscount, ...this.state.lines.map((l) => l.discount)].some((d) => d > limit + 1e-6)) {
            return `En fazla %${limit} indirim yapabilirsiniz; daha yüksek indirim için yönetici gerekir.`;
        }
        return "";
    }

    get hasConverted() {
        return this.state.lines.some((l) => l.converted);
    }

    get canSubmit() {
        return this.state.lines.length && this.state.patient && !this.discountError && !this.state.busy;
    }

    newTicket() {
        Object.assign(this.state, {
            lines: [], selected: [], globalDiscount: 0, plan: null, step: "quote",
            slots: [], booking: null, presenting: false,
        });
    }

    // ------------------------------------------------------------------
    // Patient
    // ------------------------------------------------------------------

    async onPatientInput(ev) {
        const query = ev.target.value;
        this.state.patientQuery = query;
        if (query.trim().length < 2) {
            this.state.patientResults = [];
            return;
        }
        const results = await this.orm.call("dental.quick.price", "search_patients", [query]);
        if (this.state.patientQuery === query) {
            this.state.patientResults = results;
        }
    }

    pickPatient(patient) {
        this.state.patient = patient;
        this.state.patientQuery = "";
        this.state.patientResults = [];
        this.state.newPatient = null;
    }

    clearPatient() {
        if (!this.state.plan) {
            this.state.patient = null;
        }
    }

    startNewPatient() {
        const query = this.state.patientQuery.trim();
        const looksLikePhone = /^[+\d\s()-]{5,}$/.test(query);
        this.state.newPatient = { name: looksLikePhone ? "" : query, phone: looksLikePhone ? query : "" };
        this.state.patientResults = [];
    }

    async saveNewPatient() {
        const { name, phone } = this.state.newPatient || {};
        if (!(name || "").trim()) {
            this.notification.add("Hasta adını yazın.", { type: "warning" });
            return;
        }
        const patient = await this.orm.call("dental.quick.price", "create_patient", [name, phone]);
        this.pickPatient(patient);
        this.notification.add(`${patient.name} hasta olarak eklendi.`, { type: "success" });
    }

    // ------------------------------------------------------------------
    // Plan / sharing / booking
    // ------------------------------------------------------------------

    async ensurePlan() {
        if (this.state.plan) {
            return this.state.plan;
        }
        if (!this.state.patient) {
            this.notification.add("Önce hastayı seçin ya da yeni hasta ekleyin.", { type: "warning" });
            return null;
        }
        if (this.discountError) {
            this.notification.add(this.discountError, { type: "danger" });
            return null;
        }
        this.state.busy = true;
        try {
            this.state.plan = await this.orm.call("dental.quick.price", "create_plan", [{
                patient_id: this.state.patient.id,
                currency_id: this.state.currencyId,
                global_discount: this.state.globalDiscount,
                doctor_id: this.state.doctorId,
                dentition: this.state.lines.some((l) => l.tooth && Number(l.tooth) >= 50)
                    ? (this.state.lines.some((l) => l.tooth && Number(l.tooth) < 50) ? "mixed" : "primary")
                    : "permanent",
                lines: this.state.lines.map((l) => ({
                    procedure_id: l.procedureId,
                    tooth_number: l.tooth,
                    price_unit: l.price,
                    discount: l.discount,
                    duration: l.duration,
                })),
            }]);
            this.notification.add(`Tedavi planı ${this.state.plan.name} oluşturuldu.`, { type: "success" });
            return this.state.plan;
        } finally {
            this.state.busy = false;
        }
    }

    async sendWhatsapp() {
        const plan = await this.ensurePlan();
        if (!plan) {
            return;
        }
        const share = await this.orm.call("dental.quick.price", "get_share", [plan.id]);
        if (!share.has_phone) {
            this.notification.add("Hastanın telefonu yok: WhatsApp'ta alıcıyı seçmeniz gerekecek.", { type: "warning" });
        }
        window.open(share.whatsapp_url, "_blank", "noopener");
    }

    async openPdf() {
        const plan = await this.ensurePlan();
        if (plan) {
            const share = await this.orm.call("dental.quick.price", "get_share", [plan.id]);
            window.open(share.report_url, "_blank", "noopener");
        }
    }

    async openPlan() {
        const plan = await this.ensurePlan();
        if (plan) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "dental.treatment.plan",
                res_id: plan.id,
                views: [[false, "form"]],
            });
        }
    }

    async startBooking() {
        const plan = await this.ensurePlan();
        if (!plan) {
            return;
        }
        if (!this.state.doctorId) {
            this.notification.add("Tanımlı hekim yok.", { type: "warning" });
            return;
        }
        this.state.step = "book";
        await this.loadSlots();
    }

    async loadSlots() {
        if (!this.state.doctorId || !this.state.day) {
            this.state.slots = [];
            return;
        }
        this.state.slotsLoading = true;
        try {
            this.state.slots = await this.orm.call("dental.quick.price", "get_slots",
                [this.state.doctorId, this.state.day, this.totalDuration]);
        } finally {
            this.state.slotsLoading = false;
        }
    }

    async setDoctor(ev) {
        this.state.doctorId = parseInt(ev.target.value) || null;
        await this.loadSlots();
    }

    async setDay(ev) {
        this.state.day = ev.target.value;
        await this.loadSlots();
    }

    async shiftDay(days) {
        const date = new Date(`${this.state.day}T12:00:00`);
        date.setDate(date.getDate() + days);
        this.state.day = toUtcString(date);
        await this.loadSlots();
    }

    get dayLabel() {
        try {
            return new Date(`${this.state.day}T12:00:00`).toLocaleDateString(document.documentElement.lang || "tr-TR",
                { weekday: "long", day: "numeric", month: "long" });
        } catch {
            return this.state.day;
        }
    }

    async book(slot) {
        this.state.busy = true;
        try {
            this.state.booking = await this.orm.call("dental.quick.price", "book_first_session",
                [this.state.plan.id, this.state.doctorId, slot.start]);
            this.state.step = "done";
        } catch (error) {
            await this.loadSlots();
            throw error;
        } finally {
            this.state.busy = false;
        }
    }

    openAppointment() {
        if (this.state.booking?.appointment_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "dental.appointment",
                res_id: this.state.booking.appointment_id,
                views: [[false, "form"]],
            });
        }
    }

    present(open = true) {
        this.state.presenting = open && this.state.lines.length > 0;
    }

    _onKeydown(ev) {
        if (ev.key === "Escape") {
            if (this.state.presenting) {
                this.state.presenting = false;
            } else if (this.state.step === "book") {
                this.state.step = "quote";
            } else {
                this.state.selected = [];
            }
        } else if (ev.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
            ev.preventDefault();
            this.searchRef.el?.focus();
        }
    }

    onSearchKeydown(ev) {
        if (ev.key === "Enter") {
            const first = this.visibleProcedures.find((p) => this.procedureAllowed(p));
            if (first) {
                this.addProcedure(first);
            }
        }
    }
}

registry.category("actions").add("dentistclinic.quick_price", QuickPrice);

// ----------------------------------------------------------------------
// Systray button
// ----------------------------------------------------------------------

export class QuickPriceSystray extends Component {
    static template = "dentistclinic.QuickPriceSystray";
    static props = {};

    setup() {
        this.action = useService("action");
        this.state = useState({ allowed: false });
        onWillStart(async () => {
            this.state.allowed = await user.hasGroup("dentistclinic.group_dentistclinic_user");
        });
    }

    open() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "dentistclinic.quick_price",
            name: "Hızlı Fiyat",
        });
    }
}

registry.category("systray").add("dentistclinic.quick_price", { Component: QuickPriceSystray }, { sequence: 40 });
