import { motion, AnimatePresence } from 'framer-motion';
import { FiX } from 'react-icons/fi';

export function Modal({ show, onHide, title, children, size = 'md', footer }) {
  const sizeClass = {
    sm: 'modal-sm',
    md: '',
    lg: 'modal-lg',
    xl: 'modal-xl',
  }[size];

  return (
    <AnimatePresence>
      {show && (
        <>
          <motion.div
            className="modal-backdrop show"
            style={{ zIndex: 1050 }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onHide}
          />
          <div className="modal show d-block" style={{ zIndex: 1055 }} tabIndex={-1}>
            <motion.div
              className={`modal-dialog modal-dialog-centered ${sizeClass}`}
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            >
              <div className="modal-content border-0 shadow-lg" style={{ borderRadius: 'var(--apex-radius-lg)' }}>
                <div className="modal-header border-0 pb-0">
                  <h5 className="modal-title fw-bold">{title}</h5>
                  <button type="button" className="btn-close" onClick={onHide} aria-label="Close">
                    <FiX />
                  </button>
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