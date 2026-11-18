/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.DentistClinicEvents = publicWidget.Widget.extend({
    selector: ".s_dental_events",
    events: {
        "click .dental-event-apply": "_onApply",
    },

    async start() {
        await this._super(...arguments);
        this.listEl = this.el.querySelector(".dental-event-list");
        this.placeholderNodes = [...this.listEl.childNodes].map((node) => node.cloneNode(true));
        await this._render();
    },

    destroy() {
        // Editör açılırken çizilen kartların sayfa HTML'ine kaydedilmesini önler.
        if (this.listEl) {
            this.listEl.replaceChildren(...this.placeholderNodes);
        }
        this._super(...arguments);
    },

    async _render() {
        let result;
        try {
            const response = await fetch("/dentistclinic/events/data", {
                headers: { Accept: "application/json" },
            });
            result = await response.json();
        } catch {
            result = { success: false };
        }
        if (!result.success) {
            this._message(_t("Events could not be loaded right now."));
            return;
        }
        if (!result.events.length) {
            this._message(
                _t("No events are scheduled right now. Leave your city in the form and we’ll let you know when we plan one nearby.")
            );
            return;
        }
        this.listEl.replaceChildren(...result.events.map((event) => this._card(event)));
    },

    _card(event) {
        const col = document.createElement("div");
        col.className = "col-md-6 col-lg-4 mb-4";
        const card = document.createElement("article");
        card.className = "dental-event-card h-100";
        if (event.image_url) {
            card.classList.add("dental-event-card--media");
            const media = document.createElement("div");
            media.className = "dental-event-card__media";
            const image = document.createElement("img");
            image.src = event.image_url;
            image.alt = event.name;
            image.loading = "lazy";
            image.decoding = "async";
            media.appendChild(image);
            card.appendChild(media);
        }

        const date = document.createElement("p");
        date.className = "dental-event-card__date";
        date.textContent = event.date_label;

        const title = document.createElement("h3");
        title.className = "h5 mb-1";
        title.textContent = event.name;

        const place = document.createElement("p");
        place.className = "dental-event-card__place";
        place.textContent = [event.city, event.country].filter(Boolean).join(", ");
        card.append(date, title, place);

        if (event.venue || event.address) {
            const venue = document.createElement("p");
            venue.className = "small text-muted mb-2";
            venue.textContent = [event.venue, event.address].filter(Boolean).join(" · ");
            card.appendChild(venue);
        }
        if (event.description) {
            const description = document.createElement("p");
            description.className = "small mb-2";
            description.textContent = event.description;
            card.appendChild(description);
        }
        if (event.doctors.length) {
            const doctors = document.createElement("p");
            doctors.className = "small mb-2";
            const label = document.createElement("strong");
            label.textContent = _t("Dentists:") + " ";
            doctors.append(label, event.doctors.join(", "));
            card.appendChild(doctors);
        }

        const footer = document.createElement("div");
        footer.className = "dental-event-card__footer";
        if (event.seats_available !== null && !event.is_full) {
            const seats = document.createElement("span");
            seats.className = "small text-muted";
            seats.textContent = _t("%s places left", event.seats_available);
            footer.appendChild(seats);
        }
        const button = document.createElement("a");
        button.className = "btn btn-primary btn-sm ms-auto dental-event-apply";
        button.href = "#event-request";
        if (event.is_full) {
            button.classList.add("disabled");
            button.setAttribute("aria-disabled", "true");
            button.textContent = _t("Fully booked");
        } else {
            button.dataset.eventId = event.id;
            button.textContent = _t("Apply now");
        }
        footer.appendChild(button);
        card.appendChild(footer);
        col.appendChild(card);
        return col;
    },

    _onApply(ev) {
        const eventId = ev.currentTarget.dataset.eventId;
        const select = document.querySelector(".dental-event-request-form select[name='event_id']");
        if (!eventId || !select) {
            return;
        }
        ev.preventDefault();
        select.value = eventId;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        select.closest(".s_dental_event_request").scrollIntoView({ behavior: "smooth", block: "start" });
        select.focus({ preventScroll: true });
    },

    _message(text) {
        const message = document.createElement("p");
        message.className = "col-12 text-center text-muted";
        message.textContent = text;
        this.listEl.replaceChildren(message);
    },
});

export default publicWidget.registry.DentistClinicEvents;
