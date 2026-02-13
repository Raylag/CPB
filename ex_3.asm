.686
.model flat, stdcall
option casemap:none

includelib kernel32.lib
ExitProcess proto stdcall :dword

.data
    arr dw 10, -5, 23, 8, -12, 17, 3, -1, 0, 14, 
           -7, 6, 22, -3, 9, 11, -8, 4, 19, -2, 
            5, -6, 13, 1, -9, 15, -4, 18, 2, -10, 
            7, 16
    avg dw ?           

.code
start:
    
    xor eax, eax        
    xor esi, esi        
    mov ecx, 32         

sum_loop:
    movsx ebx, word ptr arr[esi]   
    add eax, ebx                 
    add esi, 2                  
    loop sum_loop               

   
    cdq                         
    mov ecx, 32
    idiv ecx                    
    mov avg, ax                 
    
    xor esi, esi                
    mov ecx, 32                
    mov bx, avg                

process_loop:
    mov ax, word ptr arr[esi]  
    cmp ax, bx                 
    jge not_less              
    
    add ax, ax
    mov word ptr arr[esi], ax  

not_less:
    add esi, 2                
    loop process_loop

    invoke ExitProcess, 0
end start
