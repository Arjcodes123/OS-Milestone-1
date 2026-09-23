target remote localhost:26000
break sys_exec
continue
backtrace
info registers a0 a1 a2
info registers ra sp
x/4i $pc
stepi
stepi
stepi
info registers a0
