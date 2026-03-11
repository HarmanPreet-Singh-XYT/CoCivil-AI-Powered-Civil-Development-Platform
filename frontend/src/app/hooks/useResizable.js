import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Reusable panel resize hook.
 *
 * @param {object} opts
 * @param {number}  opts.defaultSize   - initial size in px
 * @param {number}  opts.minSize       - minimum allowed size in px
 * @param {number}  opts.maxSize       - maximum allowed size in px
 * @param {'horizontal'|'vertical'} opts.axis - resize direction
 * @param {boolean} [opts.reverse]     - true when dragging left/up should grow (right/bottom panels)
 * @param {string}  [opts.cssVar]      - CSS custom property to update on :root (e.g. '--panel-width')
 * @param {boolean} [opts.disabled]    - disable resizing (e.g. sidebar collapsed)
 *
 * @returns {{ size, isResizing, handleProps }}
 *   - size: current size in px
 *   - isResizing: true while dragging
 *   - handleProps: spread onto the resize handle div
 */
export default function useResizable({
  defaultSize,
  minSize,
  maxSize,
  axis = 'horizontal',
  reverse = false,
  cssVar,
  disabled = false,
}) {
  const [size, setSize] = useState(defaultSize);
  const [isResizing, setIsResizing] = useState(false);
  const startPosRef = useRef(null);
  const startSizeRef = useRef(null);

  // Sync CSS variable
  useEffect(() => {
    if (cssVar) {
      document.documentElement.style.setProperty(cssVar, `${size}px`);
    }
  }, [cssVar, size]);

  // Kill transitions on all layout elements while dragging
  useEffect(() => {
    const id = 'resize-no-transition';
    if (isResizing) {
      const style = document.createElement('style');
      style.id = id;
      style.textContent = `
        #sidebar, #search-container, #chat-panel, #policy-panel, .panel-reopen-tab {
          transition: none !important;
        }
      `;
      document.head.appendChild(style);
    }
    return () => document.getElementById(id)?.remove();
  }, [isResizing]);

  const onMouseDown = useCallback(
    (e) => {
      if (disabled) return;
      e.preventDefault();
      setIsResizing(true);
      startPosRef.current = axis === 'horizontal' ? e.clientX : e.clientY;
      startSizeRef.current = size;
    },
    [disabled, axis, size],
  );

  useEffect(() => {
    if (!isResizing) return;

    const onMove = (e) => {
      const pos = axis === 'horizontal' ? e.clientX : e.clientY;
      const delta = pos - startPosRef.current;
      const adjusted = reverse ? -delta : delta;
      setSize(Math.min(maxSize, Math.max(minSize, startSizeRef.current + adjusted)));
    };

    const onUp = () => setIsResizing(false);

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
  }, [isResizing, axis, reverse, minSize, maxSize]);

  const handleStyle = {
    position: 'absolute',
    [axis === 'horizontal' ? 'top' : 'left']: 0,
    [axis === 'horizontal' ? 'bottom' : 'right']: 0,
    [axis === 'horizontal' ? 'width' : 'height']: 4,
    cursor: axis === 'horizontal' ? 'col-resize' : 'row-resize',
    zIndex: 30,
    background: isResizing ? 'rgba(200,165,92,0.3)' : 'transparent',
    transition: 'background 0.15s',
  };

  const handleProps = {
    onMouseDown,
    onMouseEnter: (e) => {
      if (!isResizing) e.currentTarget.style.background = 'rgba(200,165,92,0.15)';
    },
    onMouseLeave: (e) => {
      if (!isResizing) e.currentTarget.style.background = 'transparent';
    },
    style: handleStyle,
  };

  return { size, isResizing, handleProps };
}
