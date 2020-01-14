
#define __Unpack_case_t(TYPENAME) \
        case TYPENAME##_ENUM :\
            *flags = ((__IEC_##TYPENAME##_t *)varp)->flags;\
            forced_value_p = *real_value_p = &((__IEC_##TYPENAME##_t *)varp)->value;\
            break;

#define __Unpack_case_p(TYPENAME)\
        case TYPENAME##_O_ENUM :\
            *flags = __IEC_OUTPUT_FLAG;\
        case TYPENAME##_P_ENUM :\
            *flags |= ((__IEC_##TYPENAME##_p *)varp)->flags;\
            *real_value_p = ((__IEC_##TYPENAME##_p *)varp)->value;\
            forced_value_p = &((__IEC_##TYPENAME##_p *)varp)->fvalue;\
            break;

#define __Is_a_string(dsc) (dsc->type == STRING_ENUM)   ||\
                           (dsc->type == STRING_P_ENUM) ||\
                           (dsc->type == STRING_O_ENUM)

static void* UnpackVar(__Unpack_desc_type *dsc, void **real_value_p, char *flags)
{
    void *varp = dsc->ptr;
    void *forced_value_p = NULL;
    *flags = 0;
    /* find data to copy*/
    switch(dsc->type){
        __ANY(__Unpack_case_t)
        __ANY(__Unpack_case_p)
    default:
        break;
    }
    if (*flags & __IEC_FORCE_FLAG)
        return forced_value_p;
    return *real_value_p;
}

