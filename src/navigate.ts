export const navigate = (
    _node: any,
    path: string,
    replace: boolean = true
) => {
    if (replace) {
        history.replaceState(null, "", path);
    } else {
        history.pushState(null, "", path);
    }
};