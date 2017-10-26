def isoformatseconds(dt):
    try:
        return dt.isoformat(timespec="seconds")
    except TypeError:
        # Python 3.5 and below
        # 'timespec' is an invalid keyword argument for this function
        return dt.isoformat().split(".")[0]
