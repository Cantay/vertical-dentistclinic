/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

const LAST_STEP = 4;

publicWidget.registry.DentistClinicBookingWizard = publicWidget.Widget.extend({
    selector: ".s_dental_booking",
    events: {
        "click .dental-booking-next": "_onNext",
        "click .dental-booking-back": "_onBack",
        "click .dental-booking-submit": "_onSubmit",
        "change select[name='doctor_id']": "_loadSlots",
        "change input[name='booking_date']": "_loadSlots",
        "click .dental-booking-slot": "_onSlotClick",
    },

    async start() {
        this.form = this.el.querySelector(".dental-booking-form");
        this.statusEl = this.el.querySelector(".dental-booking-status");
        this.slotsEl = this.el.querySelector(".dental-booking-slots");
        this.doctorSelect = this.form.querySelector("select[name='doctor_id']");
        this.dateInput = this.form.querySelector("input[name='booking_date']");
        this.slotInput = this.form.querySelector("input[name='slot_start']");
        this.step = 1;
        this.selectedSlotLabel = "";
        await this._super(...arguments);
        await this._loadDoctors();
    },

    // --- Veri yükleme ---

    async _getJson(url) {
        try {
            const response = await fetch(url, { headers: { Accept: "application/json" } });
            return await response.json();
        } catch {
            return { success: false, error: _t("Connection error, please refresh the page.") };
        }
    },

    async _loadDoctors() {
        const result = await this._getJson("/dentistclinic/booking/doctors");
        this.doctorSelect.replaceChildren();
        if (!result.success) {
            this._setStatus("is-error", result.error);
            this._addOption("", _t("No dentist found"));
            return;
        }
        this._addOption("", result.doctors.length ? _t("Choose a dentist") : _t("No dentists are available for online booking"));
        for (const doctor of result.doctors) {
            this._addOption(doctor.id, doctor.name);
        }
        const today = new Date();
        const maxDay = new Date();
        maxDay.setDate(today.getDate() + result.days_ahead);
        this.dateInput.min = this._isoDate(today);
        this.dateInput.max = this._isoDate(maxDay);
    },

    async _loadSlots() {
        this.slotInput.value = "";
        this.selectedSlotLabel = "";
        const doctorId = this.doctorSelect.value;
        const day = this.dateInput.value;
        if (!doctorId || !day) {
            this._renderSlotMessage(_t("Choose a dentist and a date to see available times."));
            return;
        }
        this._renderSlotMessage(_t("Loading available times..."));
        const params = new URLSearchParams({ doctor_id: doctorId, date: day });
        const result = await this._getJson(`/dentistclinic/booking/slots?${params}`);
        if (!result.success) {
            this._renderSlotMessage(result.error);
            return;
        }
        if (!result.slots.length) {
            this._renderSlotMessage(_t("No times are available on this date, please choose another day."));
            return;
        }
        this.slotsEl.replaceChildren();
        for (const slot of result.slots) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "btn btn-outline-primary dental-booking-slot";
            button.dataset.start = slot.start;
            button.textContent = slot.label;
            this.slotsEl.appendChild(button);
        }
    },

    _onSlotClick(ev) {
        const button = ev.currentTarget;
        for (const el of this.slotsEl.querySelectorAll(".dental-booking-slot")) {
            el.classList.toggle("active", el === button);
        }
        this.slotInput.value = button.dataset.start;
        this.selectedSlotLabel = button.textContent;
        this._setStatus("", "");
    },

    // --- Adım yönetimi ---

    _onNext() {
        const error = this._validateStep(this.step);
        if (error) {
            this._setStatus("is-error", error);
            return;
        }
        this._setStatus("", "");
        if (this.step === LAST_STEP - 1) {
            this._fillSummary();
        }
        this._goTo(this.step + 1);
    },

    _onBack() {
        this._setStatus("", "");
        this._goTo(this.step - 1);
    },

    _goTo(step) {
        this.step = Math.min(Math.max(step, 1), LAST_STEP);
        for (const el of this.form.querySelectorAll(".dental-booking-step")) {
            el.classList.toggle("d-none", Number(el.dataset.step) !== this.step);
        }
        for (const el of this.el.querySelectorAll(".dental-booking-progress li")) {
            const elStep = Number(el.dataset.step);
            el.classList.toggle("is-active", elStep === this.step);
            el.classList.toggle("is-done", elStep < this.step);
        }
        this.el.querySelector(".dental-booking-back").classList.toggle("d-none", this.step === 1);
        this.el.querySelector(".dental-booking-next").classList.toggle("d-none", this.step === LAST_STEP);
        this.el.querySelector(".dental-booking-submit").classList.toggle("d-none", this.step !== LAST_STEP);
    },

    _validateStep(step) {
        if (step === 2) {
            if (!this.doctorSelect.value) {
                return _t("Please choose a dentist.");
            }
            if (!this.slotInput.value) {
                return _t("Please choose an available time.");
            }
        }
        if (step === 3) {
            if (!this.form.elements.name.value.trim()) {
                return _t("Full name is required.");
            }
            if (!this.form.elements.phone.value.trim()) {
                return _t("Phone is required.");
            }
            const email = this.form.elements.email;
            if (email.value.trim() && !email.checkValidity()) {
                return _t("Please enter a valid email address.");
            }
        }
        return "";
    },

    _fillSummary() {
        const typeInput = this.form.querySelector("input[name='appointment_type']:checked");
        const typeLabel = typeInput ? typeInput.closest("label").textContent.trim() : "";
        const doctorLabel = this.doctorSelect.selectedOptions[0]?.textContent || "";
        const dayLabel = new Date(`${this.dateInput.value}T00:00:00`).toLocaleDateString();
        const values = {
            type: typeLabel,
            doctor: doctorLabel,
            slot: `${dayLabel} ${this.selectedSlotLabel}`,
            name: this.form.elements.name.value.trim(),
            phone: this.form.elements.phone.value.trim(),
        };
        for (const [key, value] of Object.entries(values)) {
            this.el.querySelector(`[data-summary='${key}']`).textContent = value;
        }
    },

    // --- Gönderim ---

    async _onSubmit() {
        const submitButton = this.el.querySelector(".dental-booking-submit");
        submitButton.disabled = true;
        this._setStatus("", "");
        const formData = new FormData(this.form);
        if (odoo.csrf_token) {
            formData.append("csrf_token", odoo.csrf_token);
        }
        try {
            const response = await fetch("/dentistclinic/booking/submit", {
                method: "POST",
                body: formData,
                headers: { Accept: "application/json" },
            });
            const result = await response.json();
            if (!result.success) {
                this._setStatus("is-error", result.error || _t("Your appointment request could not be sent."));
                if (result.slot_taken) {
                    this._goTo(2);
                    await this._loadSlots();
                }
                return;
            }
            if (this.el.dataset.successPage) {
                // Per-site redirect (thank-you page / conversion tracking).
                window.location.assign(this.el.dataset.successPage);
                return;
            }
            this._showDone(result.message);
        } catch {
            this._setStatus("is-error", _t("Your appointment request could not be sent, please try again."));
        } finally {
            submitButton.disabled = false;
        }
    },

    _showDone(message) {
        for (const el of this.form.querySelectorAll(".dental-booking-step, .dental-booking-nav")) {
            el.classList.add("d-none");
        }
        this.el.querySelector(".dental-booking-progress").classList.add("d-none");
        const done = this.form.querySelector(".dental-booking-done");
        done.querySelector(".dental-booking-done-message").textContent = message;
        done.classList.remove("d-none");
    },

    // --- Yardımcılar ---

    _addOption(value, label) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        this.doctorSelect.appendChild(option);
    },

    _renderSlotMessage(message) {
        const p = document.createElement("p");
        p.className = "text-muted mb-0";
        p.textContent = message;
        this.slotsEl.replaceChildren(p);
    },

    _isoDate(date) {
        const pad = (n) => String(n).padStart(2, "0");
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
    },

    _setStatus(statusClass, message) {
        this.statusEl.className = "dental-booking-status";
        if (!message) {
            this.statusEl.classList.add("d-none");
            this.statusEl.textContent = "";
            return;
        }
        if (statusClass) {
            this.statusEl.classList.add(statusClass);
        }
        this.statusEl.textContent = message;
    },
});

export default publicWidget.registry.DentistClinicBookingWizard;
