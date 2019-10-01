import { LitElement, customElement, CSSResultArray, css, TemplateResult, html, property } from "lit-element";
import { HacsStyle } from "../style/hacs-style"

@customElement("hacs-authors")
export class Authors extends LitElement {
    @property()
    public authors!: [string];

    protected render(): TemplateResult | void {
        if (String(this.authors.length) === "0") return html``
        return html`
            <div class="autors">
            <p><b>Authors: </b>

            ${this.authors.map(author =>
            html`
                <a href="https://github.com/${author.replace("@", "")}"
                        target="_blank" rel='noreferrer'>
                    ${author.replace("@", "")}
                </a>`)}

            </p>
            </div>
            `;
    }

    static get styles(): CSSResultArray {
        return [HacsStyle, css`
            .autors {

            }
        `]
    }
}