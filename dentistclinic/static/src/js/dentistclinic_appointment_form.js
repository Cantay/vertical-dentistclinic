/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.DentistClinicOnlineAppointmentForm = publicWidget.Widget.extend({
    selector: ".s_dental_appointment",
    events: {
        "submit .dental-appointment-form": "_onSubmit",
    },

    start() {
        this.statusEl = this.el.querySelector(".dental-appointment-status");
        this.submitButton = this.el.querySelector(".dental-appointment-submit");
        this.submitLabel = this.submitButton?.querySelector("span");
        this.defaultSubmitLabel = this.submitLabel?.textContent || _t("Request Appointment");
        return this._super(...arguments);
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        const form = ev.currentTarget;
        const formData = new FormData(form);
        if (odoo.csrf_token) {
            formData.append("csrf_token", odoo.csrf_token);
        }

        this._toggleSubmitting(true);
        this._setStatus("", "");

        try {
            const response = await fetch("/dentistclinic/appointment/submit", {
                method: "POST",
                body: formData,
                headers: {
                    Accept: "application/json",
                },
            });
            const result = await response.json();
            if (!response.ok || !result.success) {
                throw new Error(result.error || _t("Your appointment request could not be sent."));
            }
            form.reset();
            if (this.el.dataset.successPage) {
                // Per-site redirect (thank-you page / conversion tracking).
                window.location.assign(this.el.dataset.successPage);
                return;
            }
            this._setStatus("is-success", result.message);
        } catch (error) {
            this._setStatus("is-error", error.message || _t("Your appointment request could not be sent."));
        } finally {
            this._toggleSubmitting(false);
        }
    },

    _toggleSubmitting(isSubmitting) {
        if (this.submitButton) {
            this.submitButton.disabled = isSubmitting;
        }
        if (this.submitLabel) {
            this.submitLabel.textContent = isSubmitting ? _t("Sending...") : this.defaultSubmitLabel;
        }
    },

    _setStatus(statusClass, message) {
        if (!this.statusEl) {
            return;
        }
        this.statusEl.className = "dental-appointment-status";
        if (!message) {
            this.statusEl.classList.add("d-none");
            this.statusEl.textContent = "";
            return;
        }
        this.statusEl.classList.remove("d-none");
        if (statusClass) {
            this.statusEl.classList.add(statusClass);
        }
        this.statusEl.textContent = message;
    },
});

export default publicWidget.registry.DentistClinicOnlineAppointmentForm;
