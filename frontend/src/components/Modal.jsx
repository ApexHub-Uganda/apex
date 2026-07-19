import { motion, AnimatePresence } from 'framer-motion';

export function Modal({ show, onHide, title, children, size = 'md', footer }) {
  const sizeClass = {
    sm: 'modal-sm',
    md: '',
    lg: 'modal-lg',
    xl: 'modal-xl',
  }[size];

  const canDismiss = typeof onHide === 'function';

  return (
    <AnimatePresence>
      {show && (
        <>
          <motion.div
            className="apex-modal-backdrop"
            style={{ zIndex: 1050 }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18, ease: [0.4, 0, 0.2, 1] }}
            onClick={canDismiss ? onHide : undefined}
            aria-hidden
          />
          <div className="modal show d-block apex-modal" style={{ zIndex: 1055 }} tabIndex={-1}>
            <motion.div
              className={`modal-dialog modal-dialog-centered ${sizeClass}`}
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.97, y: 8 }}
              transition={{ type: 'spring', damping: 28, stiffness: 360, mass: 0.85 }}
            >
              <div className="modal-content border-0 apex-modal-content">
                <div className="modal-header border-0 pb-0">
                  <h5 className="modal-title fw-bold">{title}</h5>
                  {canDismiss && (
                    <button type="button" className="btn-close" onClick={onHide} aria-label="Close" />
                  )}
                </div>
                <div className="modal-body pt-3">{children}</div>
                {footer && <div className="modal-footer border-0 pt-0">{footer}</div>}
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

export default Modal;