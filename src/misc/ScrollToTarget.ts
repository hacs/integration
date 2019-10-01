/**
 * Scroll to a specific y coordinate.
 *
 * Copied from paper-scroll-header-panel.
 *
 * @method scroll
 * @param {number} top The coordinate to scroll to, along the y-axis.
 * @param {boolean} smooth true if the scroll position should be smoothly adjusted.
 */
export default function scrollToTarget(element, target) {
    // the scroll event will trigger _updateScrollState directly,
    // However, _updateScrollState relies on the previous `scrollTop` to update the states.
    // Calling _updateScrollState will ensure that the states are synced correctly.
    const top = 0;
    const scroller = target;
    const easingFn = function easeOutQuad(t, b, c, d) {
        /* eslint-disable no-param-reassign, space-infix-ops, no-mixed-operators */
        t /= d;
        return -c * t * (t - 2) + b;
        /* eslint-enable no-param-reassign, space-infix-ops, no-mixed-operators */
    };
    const animationId = Math.random();
    const duration = 200;
    const startTime = Date.now();
    const currentScrollTop = scroller.scrollTop;
    const deltaScrollTop = top - currentScrollTop;
    element._currentAnimationId = animationId;
    (function updateFrame() {
        const now = Date.now();
        const elapsedTime = now - startTime;
        if (elapsedTime > duration) {
            scroller.scrollTop = top;
        } else if (element._currentAnimationId === animationId) {
            scroller.scrollTop = easingFn(
                elapsedTime,
                currentScrollTop,
                deltaScrollTop,
                duration
            );
            requestAnimationFrame(updateFrame.bind(element));
        }
    }.call(element));
}