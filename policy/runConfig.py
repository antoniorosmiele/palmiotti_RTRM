from Config import Config
from SysConfig import SysConfig
import argparse

def main():
    parser = argparse.ArgumentParser(description="Run configuration script.")
    parser.add_argument("--config_path", type=str, default="config.json", help="Path to the configuration file.")
    parser.add_argument("--output_path", type=str, default="out/config_output.csv", help="Path to the output file.")
    args = parser.parse_args()

    config_path = args.config_path
    output_path = args.output_path

    sysConfig = SysConfig()
    config = Config()

    cpufreq, gpufreq, maxn = sysConfig.read_sysconfig(config_path)
    sysConfig.init_sysconfig(MAXN=maxn)
    sysConfig.set_frequencies(cpufreq, gpufreq, MAXN=maxn)
    config.read_config(config_path)
    config.run()
    config.export_heartbeats(output_path=output_path)
    sysConfig.restore_sysconfig(MAXN=maxn)

if __name__ == "__main__":
    main()