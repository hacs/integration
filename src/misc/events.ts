import { createCollection, Connection } from "home-assistant-js-websocket";
import { Themes } from "../types";

const fetchThemes = (conn) =>
    conn.sendMessagePromise({
        type: "frontend/get_themes",
    });

const subscribeUpdates = (conn, store) =>
    conn.subscribeEvents(
        (event) => store.setState(event.data, true),
        "themes_updated"
    );

export const subscribeThemes = (
    conn: Connection,
    onChange: (themes: Themes) => void
) =>
    createCollection<Themes>(
        "_thm",
        fetchThemes,
        subscribeUpdates,
        conn,
        onChange
    );