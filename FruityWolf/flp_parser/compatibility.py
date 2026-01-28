import sys
import enum
import logging
import contextlib

logger = logging.getLogger(__name__)

@contextlib.contextmanager
def flp_enum_patch():
    """
    Robust patch for PyFLP compatibility with Python 3.12+.
    
    PyFLP uses 'virtual' Enums (EventEnum and subclasses) which have no members
    and use __new__ and _missing_ for dynamic value lookup.
    
    Python 3.12+ (specifically EnumMeta.__call__) prohibits calling an Enum
    that has no members.
    """
    try:
        from enum import EnumMeta
        
        _orig_call = EnumMeta.__call__
        
        def safe_call(cls, *args, **kwargs):
            # Try original call first
            try:
                return _orig_call(cls, *args, **kwargs)
            except (TypeError, ValueError) as e:
                # If it failed with "no members" error (TypeError) 
                # or "not a valid value" (ValueError)
                # AND it's a PyFLP-related class, we bypass.
                
                class_str = str(cls)
                is_pyflp_enum = any(name in class_str for name in ('EventEnum', 'PluginID', 'ProjectID', 'FileFormat'))
                
                # Check for empty members error or simply any error on these classes
                if is_pyflp_enum and len(args) >= 1:
                    # We check for int-like Enums which PyFLP uses
                    if issubclass(cls, int):
                        # Bypass Enum logic and create instance directly
                        val = args[0]
                        # We must ensure we don't cause recursion if we call cls(val)
                        # So we use the underlying __new__ logic
                        try:
                            # Try class's own __new__ first
                            obj = cls.__new__(cls, *args, **kwargs)
                            if not hasattr(obj, '_value_'):
                                obj._value_ = val
                            return obj
                        except:
                            # Fallback to pure int creation
                            obj = int.__new__(cls, val)
                            obj._value_ = val
                            return obj
                
                # If NOT a PyFLP enum or bypass failed, re-raise
                raise

        # Also need to handle the functional API empty Enum('Name', {}) error
        # which happens BEFORE safe_call intercepts (it happens inside orig_call)
        
        def safe_call_v2(cls, *args, **kwargs):
            # Intercept functional API creation Enum('Name', source)
            if len(args) >= 2 and isinstance(args[0], str) and issubclass(cls, enum.Enum):
                source = args[1]
                if isinstance(source, (dict, list, tuple)) and not source:
                    # Inject dummy to avoid TypeError
                    new_args = list(args)
                    if isinstance(source, dict): new_args[1] = {'__PATCH_DUMMY__': 0}
                    else: new_args[1] = ['__PATCH_DUMMY__']
                    args = tuple(new_args)
            elif len(args) == 1 and isinstance(args[0], str) and issubclass(cls, enum.Enum) and kwargs.get('names') == {}:
                kwargs['names'] = {'__PATCH_DUMMY__': 0}

            return safe_call(cls, *args, **kwargs)

        # Apply patch
        EnumMeta.__call__ = safe_call_v2
        yield
        
    except Exception as e:
        logger.error(f"Enum patch failed: {e}")
        raise 
    finally:
        # Restore
        try:
            EnumMeta.__call__ = _orig_call
        except:
            pass
