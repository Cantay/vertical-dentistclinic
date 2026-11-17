/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.DentistClinicTeam = publicWidget.Widget.extend({
    selector: ".s_dental_team",

    async start() {
        await this._super(...arguments);
        this.listEl = this.el.querySelector(".dental-team-list");
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
            const response = await fetch(`/dentistclinic/team/data?lang=${encodeURIComponent((document.documentElement.lang || "").replace("-", "_"))}`, {
                headers: { Accept: "application/json" },
            });
            result = await response.json();
        } catch {
            result = { success: false };
        }
        if (!result.success) {
            this._message(_t("Team information could not be loaded right now."));
            return;
        }
        if (!result.members.length) {
            this._message(_t("No team members have been published yet."));
            return;
        }
        const nodes = [];
        result.members.forEach((member, index) => {
            nodes.push(this._card(member));
            if (member.separator_after && index < result.members.length - 1) {
                const separator = document.createElement("div");
                separator.className = "col-12 my-4";
                separator.setAttribute("role", "separator");
                const line = document.createElement("hr");
                line.className = "m-0";
                separator.appendChild(line);
                if (member.separator_title) {
                    const heading = document.createElement("div");
                    heading.className = "dental-team-separator";
                    const title = document.createElement("h3");
                    title.className = "dental-team-separator__title";
                    title.textContent = member.separator_title;
                    heading.appendChild(title);
                    if (member.separator_text) {
                        const text = document.createElement("p");
                        text.className = "dental-team-separator__text";
                        text.textContent = member.separator_text;
                        heading.appendChild(text);
                    }
                    separator.appendChild(heading);
                }
                nodes.push(separator);
            }
        });
        this.listEl.replaceChildren(...nodes);
    },

    _card(member) {
        const col = document.createElement("div");
        col.className = "col-sm-6 col-lg-3 mb-4";

        const link = document.createElement("a");
        link.href = member.profile_url;
        link.className = "dental-team-card d-block h-100 text-reset text-decoration-none";

        const photo = document.createElement("div");
        photo.className = "dental-team-card__photo";
        const img = document.createElement("img");
        img.src = member.image_url;
        img.alt = member.name;
        img.loading = "lazy";
        photo.appendChild(img);

        const body = document.createElement("div");
        body.className = "dental-team-card__body";
        const name = document.createElement("h3");
        name.className = "h5 mb-1";
        name.textContent = member.title ? `${member.title} ${member.name}` : member.name;
        body.appendChild(name);
        if (member.subtitle) {
            const subtitle = document.createElement("div");
            subtitle.className = "text-muted small mb-2";
            subtitle.textContent = member.subtitle;
            body.appendChild(subtitle);
        }
        if (member.short_bio) {
            const bio = document.createElement("p");
            bio.className = "mb-0 small";
            bio.textContent = member.short_bio;
            body.appendChild(bio);
        }
        if (member.languages?.length) {
            const langs = document.createElement("ul");
            langs.className = "dental-team-langs list-unstyled";
            for (const lang of member.languages) {
                const item = document.createElement("li");
                item.className = "dental-team-langs__item";
                const flag = document.createElement("img");
                flag.src = lang.flag_url;
                flag.alt = "";
                flag.width = 20;
                flag.height = 15;
                flag.loading = "lazy";
                const label = document.createElement("span");
                label.textContent = lang.name;
                item.append(flag, label);
                langs.appendChild(item);
            }
            body.appendChild(langs);
        }

        link.append(photo, body);
        col.appendChild(link);
        return col;
    },

    _message(text) {
        const p = document.createElement("p");
        p.className = "text-center text-muted";
        p.textContent = text;
        this.listEl.replaceChildren(p);
    },
});

export default publicWidget.registry.DentistClinicTeam;
