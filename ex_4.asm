.386
.MODEL FLAT, STDCALL
option casemap:none
.DATA
    A_OUT      EQU 8A6h    
    A_IN       EQU 8A5h    
    U0         BYTE 8Ah    
    DELTA_U    BYTE 03h    
    N_ITER     EQU 36      
    
    MASK_SR    BYTE 84h    
    MASK_RS    BYTE 18h    

    ARRAY_USRR WORD N_ITER DUP(0) 
    ARRAY_DATA BYTE N_ITER DUP(0) 

    CUR_U_HIGH BYTE ?      
    COUNTER    DWORD 1     

.CODE
START:
    mov al, U0
    mov CUR_U_HIGH, al
    mov ecx, N_ITER
    mov esi, 0           

MAIN_LOOP:
    push ecx            

WAIT_SYNC:
    mov dx, A_IN
    mov ax, 0100h        
    test ah, 1          
    jz WAIT_SYNC         

    mov ah, CUR_U_HIGH
    mov al, 0
    mov ebx, COUNTER
    test ebx, 1         
    jnz ODD_ITER        

EVEN_ITER:              
    or al, MASK_RS      
    mov bl, MASK_SR
    not bl
    and al, bl
    jmp SAVE_AND_SEND

ODD_ITER:               
    or al, MASK_SR      
    mov bl, MASK_RS
    not bl
    and al, bl

SAVE_AND_SEND:
    mov ARRAY_USRR[esi*2], ax 
    mov dx, A_OUT
              
    nop

    mov edx, 125             
DELAY_98MS:
    call DELAY_10US
    dec edx
    jnz DELAY_98MS

    mov dx, A_IN
    mov ax, 0             
    mov ARRAY_DATA[esi], al   


    mov al, CUR_U_HIGH
    add al, DELTA_U     
    mov CUR_U_HIGH, al
    
    inc COUNTER         
    inc esi              
    pop ecx              
    dec ecx
    jnz MAIN_LOOP

    ret 

DELAY_10US PROC
    push eax
    push ecx
    mov eax, 4 
L1: mov ecx, 109h 
    nop
    nop
L2: nop
    nop
    nop
    nop
    nop
    nop
    loop L2
    dec eax
    jnz L1
    pop ecx
    pop eax
    ret
DELAY_10US ENDP

END START
