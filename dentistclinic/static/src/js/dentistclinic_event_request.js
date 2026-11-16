/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.DentistClinicEventRequest = publicWidget.Widget.extend({
    selector: ".s_dental_event_request",
    events: {
        "submit .dental-event-request-form": "_onSubmit",
        "change select[name='event_id']": "_onEventChange",
    },

    async start() {
        this.form = this.el.querySelector(".dental-event-request-form");
        this.statusEl = this.el.querySelector(".dental-appointment-status");
        this.submitButton = this.el.querySelector(".dental-event-request-submit");
        this.countrySelect = this.form.querySelector("select[name='country_id']");
        this.eventSelect = this.form.querySelector("select[name='event_id']");
        this.locationEl = this.form.querySelector(".dental-event-location");
        // Editörde doldurulan seçeneklerin sayfa HTML'ine kaydedilmemesi için ilk hâl saklanır.
        this.initialOptions = [this.countrySelect, this.eventSelect]
            .filter(Boolean)
            .map((select) => [select, [...select.childNodes].map((node) => node.cloneNode(true))]);
        await this._super(...arguments);
        await Promise.all([this._loadCountries(), this._loadEvents()]);
    },

    destroy() {
        for (const [select, nodes] of this.initialOptions || []) {
            select.replaceChildren(...nodes);
        }
        this.locationEl?.classList.remove("d-none");
        this._super(...arguments);
    },

    async _loadEvents() {
        if (!this.eventSelect) {
            return;
        }
        let result;
        try {
            const response = await fetch("/dentistclinic/events/data", {
                headers: { Accept: "application/json" },
            });
            result = await response.json();
        } catch {
            result = { success: false };
        }
        const events = result.success ? result.events.filter((event) => !event.is_full) : [];
        for (const event of events) {
            const label = `${event.name} · ${event.city}, ${event.country} · ${event.date_label}`;
            this.eventSelect.appendChild(this._option(event.id, label));
        }
        this.eventSelect.closest(".mb-3").classList.toggle("d-none", !events.length);
        const requested = new URLSearchParams(window.location.search).get("event");
        if (requested && events.some((event) => String(event.id) === requested)) {
            this.eventSelect.value = requested;
        }
        this._onEventChange();
    },

    _onEventChange() {
        const hasEvent = Boolean(this.eventSelect?.value);
        this.locationEl?.classList.toggle("d-none", hasEvent);
    },

    async _loadCountries() {
        let result;
        try {
            const response = await fetch("/dentistclinic/event-request/countries", {
                headers: { Accept: "application/json" },
            });
            result = await response.json();
        } catch {
            result = { success: false, error: _t("Connection error, please refresh the page.") };
        }
        this.countrySelect.replaceChildren(this._option("", result.success ? _t("Select a country") : "-"));
        if (!result.success) {
            this._setStatus("is-error", result.error);
            this.submitButton.disabled = true;
            return;
        }
        for (const country of result.countries) {
            this.countrySelect.appendChild(this._option(country.id, country.name));
        }
    },

    _validate() {
        const els = this.form.elements;
        const hasEvent = Boolean(els.event_id?.value);
        if (!hasEvent && !els.country_id.value) {
            return _t("Please select a country.");
        }
        if (!els.contact_name.value.trim()) {
            return _t("Full name is required.");
        }
        if (!hasEvent && !els.city.value.trim()) {
            return _t("Full name and city are required.");
        }
        if (!els.phone.value.trim() && !els.email.value.trim()) {
            return _t("Please enter at least a phone number or an email address.");
        }
        if (els.email.value.trim() && !els.email.checkValidity()) {
            return _t("Please enter a valid email address.");
        }
        if (!els.privacy_consent.checked) {
            return _t("To continue, please accept the privacy notice.");
        }
        return "";
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        const error = this._validate();
        if (error) {
            this._setStatus("is-error", error);
            return;
        }
        this.submitButton.disabled = true;
        this._setStatus("", "");
        const formData = new FormData(this.form);
        if (odoo.csrf_token) {
            formData.append("csrf_token", odoo.csrf_token);
        }
        try {
            const response = await fetch("/dentistclinic/event-request/submit", {
                method: "POST",
                body: formData,
                headers: { Accept: "application/json" },
            });
            const result = await response.json();
            if (result.success) {
                this.form.reset();
                this._onEventChange();
                this._setStatus("is-success", result.message);
            } else {
                this._setStatus("is-error", result.error || _t("Your request could not be sent."));
            }
        } catch {
            this._setStatus("is-error", _t("Your request could not be sent, please try again."));
        } finally {
            this.submitButton.disabled = false;
        }
    },

    _option(value, label) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        return option;
    },

    _setStatus(statusClass, message) {
        this.statusEl.className = "dental-appointment-status";
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

export default publicWidget.registry.DentistClinicEventRequest;
