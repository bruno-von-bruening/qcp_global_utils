conda_env='qc_global_utilities'
conda_file="install/${conda_env}_conda_env.yaml"
dependencies=()

if [ ! -f ${conda_file} ]; then
   echo "The file \'${conda_file}\' does not exist"
   exit
fi

source install/setup_ext.sh
paths=( $(get_paths_for_dependencies ${dependencies[@]}) )

conda_update_env ${conda_env} ${conda_file}

conda activate ${conda_env}
if [[ $? != 0 ]]; then
   echo "Cannot activate conda environment ${conda_env}"
   exit
fi

install_pip_projects '.' ${paths[@]}

