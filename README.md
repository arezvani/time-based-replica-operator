# TBR Operator

The TBR Operator is a Kubernetes operator that manages the scaling of deployments and statefulsets based on a Time-Based Replicas (TBR) policy. It ensures that the desired number of replicas is scaled up or down during specified working hours.

## Prerequisites

Before running the TBR Operator, make sure you have the following prerequisites:

- Kubernetes cluster
- Kubernetes Python client library (`kubernetes`)
- Kopf Python library (`kopf`)

## Installation

1. Clone the TBR Operator repository:

   ```
   git clone https://github.com/example/tbr-operator.git
   ```

2. Change into the cloned directory:

   ```
   cd tbr-operator
   ```

3. Install the required Python packages:

   ```
   pip install -r requirements.txt
   ```

4. Set up the Kubernetes configuration. Uncomment one of the following lines in the code, depending on whether you want to use in-cluster configuration or load an external kubeconfig file:

   ```python
   # config.load_incluster_config()
   config.load_kube_config()
   ```

5. Set the desired check interval by setting the `CHECK_INTERVAL` environment variable. The check interval determines how frequently the TBR policies are evaluated. The value should be provided in seconds.

6. Deploy the TBR Operator to your Kubernetes cluster:

   ```
   kopf run tbr.py
   ```
   
## Build

```bash
docker build -t <image_name>:<image_version> .  $(cat build.args | sed 's@^@--build-arg @g' | paste -s -d " ")
```

## Usage

To use the TBR Operator, follow these steps:

1. Create a TBR policy custom resource. A TBR policy defines the working hours and replica count for deployments or statefulsets. Here is an example YAML manifest for a TBR policy:

   ```yaml
   apiVersion: abriment.dev/v1
   kind: tbr
   metadata:
     name: my-tbr-policy
   spec:
     startTime: "08:00"      # Start time in HH:MM format
     endTime: "18:00"        # End time in HH:MM format
     timeZone: "America/New_York"  # Timezone in TZ database name format
     replicas: 3             # Desired number of replicas during working hours
   ```

2. Apply the TBR policy to a deployment or statefulset by adding the following annotation to the metadata of the resource:

   ```yaml
   metadata:
     annotations:
       tbr.abriment.dev/policy: my-tbr-policy
   ```

3. The TBR Operator will automatically monitor the deployments and statefulsets with the TBR policy annotation. During the specified working hours, the operator will scale up the replicas to the desired count. Outside of the working hours, the operator will scale down the replicas to 0.

## Cleanup

When you want to uninstall the TBR Operator, follow these steps:

1. Delete all TBR policies:

   ```
   kubectl delete tbr -n <namepsace> <name>
   ```

2. Delete the TBR Operator deployment:

   ```
   kubectl delete deployment tbr-operator
   ```

## Contributing

If you want to contribute to the TBR Operator, feel free to fork the repository and submit pull requests. We welcome any contributions, including bug fixes, feature enhancements, and documentation improvements.

## License

The TBR Operator is released under the [MIT License](https://opensource.org/licenses/MIT). See the [LICENSE](LICENSE) file for more details.
