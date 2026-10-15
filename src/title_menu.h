#pragma once
#ifdef __cplusplus
extern "C" {
#endif
/* Bind the NEW GAME+ menu patches to the cartridge image the guest executes
 * (cart->rom). Cheap when already bound; call before every guest frame. */
void Cv4TitleMenuBind(void);
#ifdef __cplusplus
}
#endif
