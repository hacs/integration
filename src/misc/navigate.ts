export const navigate = (
    _node: any,
    path: string
) => {
    history.replaceState(null, "", path);
};