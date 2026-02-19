#!/bin/bash

#órás verif mind a 24 órára 
set -x
day=20260215
for hour in $(seq -w 00 01 02); do  # első szám az első verifikálandó időpontot megeleőző óra, mert tól-igot vár. második a lépésköz időben (gyakoriság)
 # módosítani a harmadik elemet, ha aggregálás helyett órásat akarok 
 python main.py --loglevel debug --parameter cma  --verif_dataset SAF_cma --forcedraw --forcescore --region Hungary --zoom_to_subdomain -s ${day}${hour} -d 12 -l 1 24 --custom_experiments arome_hun_test ecmwf_hun_test wrf_hun_test arome_ruc_test --custom_experiment_file custom_experiments_test --save_full_fss --save 
done


  # -l csak a forecastok listájára vonatkozik (futásra). és abból is csak arra hol keresse. arra nem mit talál. (lehet hogy kevesebbet talál, mint amekkora a run ablakot definiáltunk neki). 
  # amit nem értek, az a seq -q part. 

  # ha aggregálni akarok: akkor adok nagyobb  harmadik elemet?

  # vagy pont fordítva?

  # vagy ennek nincs is köze az aggregáláshoz?

  # ha nincs, akkor mit deffiniál? 


  #-l hour hour min max 0 24sss


  # Napi 24 órás akkumuláció

#!/bin/bash

# cloud cover duration a 24 órára 
#set -x
#day=20260208
#for hour in $(seq -w 00 01 19); do  # első szám az első verifikálandó időpontot megeleőző óra, mert tól-igot vár. második a lépésköz időben (gyakoriság)
  # módosítani a harmadik elemet, ha aggregálás helyett órásat akarok 
 #python main.py --loglevel debug --parameter cma  --verif_dataset SAF_cma --forcedraw --forcescore --region Hungary --zoom_to_subdomain -s ${day}${hour} -d 20 -l 0 --custom_experiments arome_hun_test ecmwf_hun_test --custom_experiment_file custom_experiments_test --save_full_fss --save 
#done

